"""
Exemple d'utilisation du système de seeder idempotent
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from sqlalchemy_seedify import BaseSeeder, SeederRegistry

# Configuration de la base de données (exemple avec SQLite)
engine = create_engine('sqlite:///example.db', echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modèles de données
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

# Créer les tables
Base.metadata.create_all(bind=engine)


# Exemple de seeder A - Version initiale
class UserSeederV1(BaseSeeder):
    """Version 1 du seeder utilisateur - données initiales"""
    
    def get_model(self):
        return User
    
    def get_unique_fields(self):
        return ['username', 'email']  # Champs qui définissent l'unicité
    
    def get_data(self):
        return [
            {
                'username': 'admin',
                'email': 'admin@example.com'
            },
            {
                'username': 'user1',
                'email': 'user1@example.com'
            }
        ]


# Exemple de seeder A - Version modifiée (plus de données)
class UserSeederV2(BaseSeeder):
    """Version 2 du seeder utilisateur - données étendues"""
    
    def get_model(self):
        return User
    
    def get_unique_fields(self):
        return ['username', 'email']
    
    def get_data(self):
        return [
            # Données originales (déjà en base après V1)
            {
                'username': 'admin',
                'email': 'admin@example.com'
            },
            {
                'username': 'user1',
                'email': 'user1@example.com'
            },
            # Nouvelles données ajoutées dans V2
            {
                'username': 'user2',
                'email': 'user2@example.com'
            },
            {
                'username': 'moderator',
                'email': 'moderator@example.com'
            }
        ]


class CategorySeeder(BaseSeeder):
    """Seeder pour les catégories"""
    
    def get_model(self):
        return Category
    
    def get_unique_fields(self):
        return ['name']
    
    def get_data(self):
        return [
            {
                'name': 'Technology',
                'description': 'Tech-related content'
            },
            {
                'name': 'Sports',
                'description': 'Sports and fitness content'
            }
        ]


def demonstrate_idempotent_behavior():
    """Démonstration du comportement idempotent des seeders"""
    
    session = SessionLocal()
    registry = SeederRegistry(session)
    
    print("=== DÉMONSTRATION DU COMPORTEMENT IDEMPOTENT ===\\n")
    
    # Enregistrer les seeders
    registry.register(UserSeederV1)
    registry.register(CategorySeeder)
    
    print("1. Premier lancement du seeder UserSeederV1:")
    result = registry.run('UserSeederV1')
    print(f"   Résultat: {result}\\n")
    
    print("2. Relancement du même seeder UserSeederV1 (sans modification):")
    result = registry.run('UserSeederV1')
    print(f"   Résultat: {result}\\n")
    
    print("3. Lancement du seeder CategorySeeder:")
    result = registry.run('CategorySeeder')
    print(f"   Résultat: {result}\\n")
    
    print("4. Maintenant, simulons la modification du seeder...")
    print("   On remplace UserSeederV1 par UserSeederV2 (avec plus de données)")
    
    # Remplacer par la version étendue
    registry.seeders['UserSeederV1'] = UserSeederV2  # Simulation du remplacement
    
    print("5. Lancement du seeder modifié:")
    result = registry.run('UserSeederV1')
    print(f"   Résultat: {result}\\n")
    
    print("6. Relancement du seeder modifié (pour vérifier l'idempotence):")
    result = registry.run('UserSeederV1')
    print(f"   Résultat: {result}\\n")
    
    print("7. Historique des exécutions:")
    history = registry.get_execution_history('UserSeederV1')
    for execution in history:
        print(f"   - {execution['executed_at']}: {execution['success']} - Hash: {execution['data_hash'][:8]}...")
    
    print("\\n8. Contenu final de la table users:")
    users = session.query(User).all()
    for user in users:
        print(f"   - {user.username} ({user.email})")
    
    session.close()


if __name__ == '__main__':
    demonstrate_idempotent_behavior()