"""
Core seeder implementation for idempotent database seeding
"""

import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Type, Union
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError


Base = declarative_base()


class SeederExecution(Base):
    """Table pour tracker les exécutions de seeders"""
    __tablename__ = 'seeder_executions'
    
    id = Column(String(255), primary_key=True)  # seeder_name:data_hash
    seeder_name = Column(String(255), nullable=False, index=True)
    data_hash = Column(String(64), nullable=False)  # SHA256 du contenu des données
    executed_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)


class BaseSeeder(ABC):
    """
    Classe de base pour créer des seeders idempotents.
    
    Un seeder idempotent peut être exécuté plusieurs fois sans créer de doublons.
    Il utilise un système de hachage pour détecter les nouvelles données à insérer.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.name = self.__class__.__name__
        
    @abstractmethod
    def get_data(self) -> List[Dict[str, Any]]:
        """
        Retourne la liste des données à insérer.
        Chaque élément doit être un dictionnaire représentant un enregistrement.
        """
        pass
    
    @abstractmethod
    def get_model(self):
        """
        Retourne le modèle SQLAlchemy cible pour l'insertion.
        """
        pass
    
    def get_unique_fields(self) -> List[str]:
        """
        Retourne la liste des champs qui définissent l'unicité d'un enregistrement.
        Par défaut, utilise tous les champs sauf les timestamps et IDs auto-générés.
        """
        return []
    
    def _calculate_data_hash(self, data: List[Dict[str, Any]]) -> str:
        """Calcule un hash SHA256 des données pour détecter les changements"""
        # Trier les données pour avoir un hash consistant
        sorted_data = sorted([
            {k: v for k, v in item.items()} 
            for item in data
        ], key=lambda x: json.dumps(x, sort_keys=True, default=str))
        
        data_str = json.dumps(sorted_data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _get_existing_records_hashes(self) -> Set[str]:
        """Récupère les hashes des enregistrements déjà traités par ce seeder"""
        existing_executions = (
            self.session.query(SeederExecution)
            .filter(SeederExecution.seeder_name == self.name)
            .filter(SeederExecution.success == True)
            .all()
        )
        return {execution.data_hash for execution in existing_executions}
    
    def _record_exists(self, data_item: Dict[str, Any]) -> bool:
        """Vérifie si un enregistrement existe déjà dans la base"""
        model = self.get_model()
        unique_fields = self.get_unique_fields()
        
        if not unique_fields:
            # Si pas de champs uniques définis, on utilise tous les champs
            # sauf ceux qui commencent par 'id' ou finissent par '_at'
            unique_fields = [
                key for key in data_item.keys() 
                if not (key.startswith('id') or key.endswith('_at'))
            ]
        
        query = self.session.query(model)
        for field in unique_fields:
            if field in data_item:
                query = query.filter(getattr(model, field) == data_item[field])
        
        return query.first() is not None
    
    def run(self, force: bool = False) -> Dict[str, Any]:
        """
        Exécute le seeder de manière idempotente.
        
        Args:
            force: Si True, force l'exécution même si les données n'ont pas changé
            
        Returns:
            Dictionnaire avec les statistiques d'exécution
        """
        try:
            data = self.get_data()
            if not data:
                return {
                    'seeder': self.name,
                    'status': 'success',
                    'inserted': 0,
                    'skipped': 0,
                    'message': 'No data to seed'
                }
            
            data_hash = self._calculate_data_hash(data)
            existing_hashes = self._get_existing_records_hashes()
            
            # Si ce hash existe déjà et qu'on ne force pas, on skip
            if not force and data_hash in existing_hashes:
                return {
                    'seeder': self.name,
                    'status': 'skipped',
                    'inserted': 0,
                    'skipped': len(data),
                    'message': 'Data already seeded (no changes detected)'
                }
            
            # Traitement des nouvelles données
            inserted = 0
            skipped = 0
            model = self.get_model()
            
            for item in data:
                if not self._record_exists(item):
                    try:
                        record = model(**item)
                        self.session.add(record)
                        inserted += 1
                    except Exception as e:
                        # Log l'erreur mais continue avec les autres enregistrements
                        print(f"Error inserting record {item}: {e}")
                        continue
                else:
                    skipped += 1
            
            # Commit des nouvelles données
            if inserted > 0:
                self.session.commit()
            
            # Enregistrer l'exécution
            execution_id = f"{self.name}:{data_hash}"
            execution = SeederExecution(
                id=execution_id,
                seeder_name=self.name,
                data_hash=data_hash,
                success=True
            )
            
            # Utiliser merge pour éviter les conflits si l'exécution existe déjà
            self.session.merge(execution)
            self.session.commit()
            
            return {
                'seeder': self.name,
                'status': 'success',
                'inserted': inserted,
                'skipped': skipped,
                'message': f'Successfully processed {len(data)} records'
            }
            
        except Exception as e:
            self.session.rollback()
            
            # Enregistrer l'échec
            try:
                data_hash = self._calculate_data_hash(self.get_data())
                execution_id = f"{self.name}:{data_hash}"
                execution = SeederExecution(
                    id=execution_id,
                    seeder_name=self.name,
                    data_hash=data_hash,
                    success=False,
                    error_message=str(e)
                )
                self.session.merge(execution)
                self.session.commit()
            except:
                pass  # Si on ne peut pas enregistrer l'échec, on continue
            
            return {
                'seeder': self.name,
                'status': 'error',
                'inserted': 0,
                'skipped': 0,
                'message': f'Error: {str(e)}'
            }


class SeederRegistry:
    """Registry pour gérer et exécuter les seeders"""
    
    def __init__(self, session: Session):
        self.session = session
        self.seeders: Dict[str, Type[BaseSeeder]] = {}
        
        # Créer les tables de métadonnées si elles n'existent pas
        Base.metadata.create_all(bind=session.bind)
    
    def register(self, seeder_class: Type[BaseSeeder]) -> None:
        """Enregistre un seeder dans le registry"""
        name = seeder_class.__name__
        if name in self.seeders:
            raise ValueError(f"Seeder '{name}' is already registered")
        self.seeders[name] = seeder_class
    
    def run(self, seeder_name: str, force: bool = False) -> Dict[str, Any]:
        """Exécute un seeder spécifique"""
        if seeder_name not in self.seeders:
            raise ValueError(f"Seeder '{seeder_name}' not found")
        
        seeder_class = self.seeders[seeder_name]
        seeder = seeder_class(self.session)
        return seeder.run(force=force)
    
    def run_all(self, force: bool = False) -> List[Dict[str, Any]]:
        """Exécute tous les seeders enregistrés"""
        results = []
        for seeder_name in self.seeders:
            result = self.run(seeder_name, force=force)
            results.append(result)
        return results
    
    def list_seeders(self) -> List[str]:
        """Retourne la liste des seeders enregistrés"""
        return list(self.seeders.keys())
    
    def get_execution_history(self, seeder_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère l'historique des exécutions"""
        query = self.session.query(SeederExecution)
        if seeder_name:
            query = query.filter(SeederExecution.seeder_name == seeder_name)
        
        executions = query.order_by(SeederExecution.executed_at.desc()).all()
        
        return [
            {
                'id': execution.id,
                'seeder_name': execution.seeder_name,
                'data_hash': execution.data_hash,
                'executed_at': execution.executed_at,
                'success': execution.success,
                'error_message': execution.error_message
            }
            for execution in executions
        ]