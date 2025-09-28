"""
Example of using Faker for generating test data.
"""

from datetime import datetime, timedelta
from alembic_seeder import BaseSeeder


class FakeCustomerSeeder(BaseSeeder):
    """Generate fake customer data using Faker."""
    
    @classmethod
    def _get_metadata(cls):
        from alembic_seeder.core.base_seeder import SeederMetadata
        return SeederMetadata(
            name=cls.__name__,
            description="Generate fake customers for testing",
            environments=["development", "testing"],
            priority=100,
            can_rollback=True,
            batch_size=500,
            tags=["test-data", "faker"],
        )
    
    def run(self):
        """Generate fake customers."""
        try:
            from faker import Faker
        except ImportError:
            raise ImportError("Faker is required. Install with: pip install faker")
        
        from myapp.models import Customer
        
        fake = Faker()
        Faker.seed(12345)  # For reproducible data
        
        customers = []
        num_customers = 1000
        
        for i in range(num_customers):
            customer = Customer(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.unique.email(),
                phone=fake.phone_number(),
                date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=80),
                
                # Address
                street_address=fake.street_address(),
                city=fake.city(),
                state=fake.state(),
                postal_code=fake.postcode(),
                country=fake.country(),
                
                # Profile
                username=fake.unique.user_name(),
                bio=fake.text(max_nb_chars=200),
                website=fake.url(),
                company=fake.company(),
                job_title=fake.job(),
                
                # Metadata
                registration_date=fake.date_time_between(start_date="-2y", end_date="now"),
                last_login=fake.date_time_between(start_date="-30d", end_date="now"),
                is_verified=fake.boolean(chance_of_getting_true=75),
                is_premium=fake.boolean(chance_of_getting_true=20),
                
                # Financial
                credit_score=fake.random_int(min=300, max=850),
                annual_income=fake.random_int(min=20000, max=200000, step=5000),
                
                # Preferences
                preferred_language=fake.random_element(["en", "es", "fr", "de", "ja"]),
                newsletter_subscribed=fake.boolean(chance_of_getting_true=40),
                
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            customers.append(customer)
            
            # Batch insert for better performance
            if (i + 1) % self._metadata.batch_size == 0:
                self.session.bulk_save_objects(customers)
                self.session.flush()
                customers = []
                print(f"Inserted {i + 1}/{num_customers} customers...")
        
        # Insert remaining customers
        if customers:
            self.session.bulk_save_objects(customers)
            self.session.flush()
        
        self._records_affected = num_customers
        print(f"Successfully seeded {num_customers} customers")
    
    def rollback(self):
        """Remove fake customers."""
        from myapp.models import Customer
        
        # Delete customers created in the last 2 years (matching our faker date range)
        two_years_ago = datetime.utcnow() - timedelta(days=730)
        deleted = self.session.query(Customer).filter(
            Customer.registration_date >= two_years_ago
        ).delete(synchronize_session=False)
        
        self.session.flush()
        print(f"Deleted {deleted} fake customers")


class FakeProductSeeder(BaseSeeder):
    """Generate fake product data."""
    
    @classmethod
    def _get_metadata(cls):
        from alembic_seeder.core.base_seeder import SeederMetadata
        return SeederMetadata(
            name=cls.__name__,
            description="Generate fake products for testing",
            environments=["development", "testing"],
            dependencies=["CategorySeeder"],  # Needs categories first
            priority=110,
            can_rollback=True,
            tags=["test-data", "faker", "products"],
        )
    
    def run(self):
        """Generate fake products."""
        try:
            from faker import Faker
        except ImportError:
            raise ImportError("Faker is required. Install with: pip install faker")
        
        from myapp.models import Product, Category
        import random
        
        fake = Faker()
        
        # Get existing categories
        categories = self.session.query(Category).all()
        if not categories:
            print("No categories found. Run CategorySeeder first.")
            return
        
        products = []
        num_products = 500
        
        # Product name templates
        product_templates = [
            lambda: f"{fake.word().title()} {fake.word().title()}",
            lambda: f"{fake.company()} {fake.word().title()}",
            lambda: f"Premium {fake.word().title()}",
            lambda: f"{fake.color_name()} {fake.word().title()}",
        ]
        
        for i in range(num_products):
            product = Product(
                name=random.choice(product_templates)(),
                sku=f"SKU-{fake.unique.random_number(digits=8)}",
                description=fake.paragraph(nb_sentences=5),
                short_description=fake.sentence(nb_words=10),
                
                # Pricing
                price=round(random.uniform(9.99, 999.99), 2),
                cost=round(random.uniform(5.00, 500.00), 2),
                sale_price=round(random.uniform(8.99, 899.99), 2) if fake.boolean(chance_of_getting_true=30) else None,
                
                # Inventory
                stock_quantity=fake.random_int(min=0, max=1000),
                low_stock_threshold=fake.random_int(min=5, max=50),
                
                # Attributes
                weight=round(random.uniform(0.1, 50.0), 2),
                length=round(random.uniform(1.0, 100.0), 1),
                width=round(random.uniform(1.0, 100.0), 1),
                height=round(random.uniform(1.0, 100.0), 1),
                
                # Category
                category_id=random.choice(categories).id,
                
                # Status
                is_active=fake.boolean(chance_of_getting_true=90),
                is_featured=fake.boolean(chance_of_getting_true=20),
                is_digital=fake.boolean(chance_of_getting_true=30),
                
                # SEO
                meta_title=fake.sentence(nb_words=6),
                meta_description=fake.sentence(nb_words=15),
                slug=fake.slug(),
                
                # Ratings
                rating_average=round(random.uniform(1.0, 5.0), 1),
                rating_count=fake.random_int(min=0, max=500),
                
                # Dates
                published_at=fake.date_time_between(start_date="-1y", end_date="now"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            products.append(product)
            
            # Batch insert
            if (i + 1) % 100 == 0:
                self.session.bulk_save_objects(products)
                self.session.flush()
                products = []
                print(f"Inserted {i + 1}/{num_products} products...")
        
        # Insert remaining
        if products:
            self.session.bulk_save_objects(products)
            self.session.flush()
        
        self._records_affected = num_products
        print(f"Successfully seeded {num_products} products")
    
    def rollback(self):
        """Remove fake products."""
        from myapp.models import Product
        
        # Delete products with SKU pattern
        deleted = self.session.query(Product).filter(
            Product.sku.like("SKU-%")
        ).delete(synchronize_session=False)
        
        self.session.flush()
        print(f"Deleted {deleted} fake products")


class FakeOrderSeeder(BaseSeeder):
    """Generate fake order data."""
    
    @classmethod
    def _get_metadata(cls):
        from alembic_seeder.core.base_seeder import SeederMetadata
        return SeederMetadata(
            name=cls.__name__,
            description="Generate fake orders for testing",
            environments=["development", "testing"],
            dependencies=["FakeCustomerSeeder", "FakeProductSeeder"],
            priority=120,
            can_rollback=True,
            tags=["test-data", "faker", "orders"],
        )
    
    def run(self):
        """Generate fake orders."""
        try:
            from faker import Faker
        except ImportError:
            raise ImportError("Faker is required. Install with: pip install faker")
        
        from myapp.models import Order, OrderItem, Customer, Product
        import random
        
        fake = Faker()
        
        # Get existing customers and products
        customers = self.session.query(Customer).limit(100).all()
        products = self.session.query(Product).filter_by(is_active=True).limit(200).all()
        
        if not customers or not products:
            print("No customers or products found. Run required seeders first.")
            return
        
        num_orders = 200
        order_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
        payment_methods = ["credit_card", "paypal", "stripe", "bank_transfer"]
        
        for i in range(num_orders):
            customer = random.choice(customers)
            order_date = fake.date_time_between(start_date="-6m", end_date="now")
            
            order = Order(
                customer_id=customer.id,
                order_number=f"ORD-{fake.unique.random_number(digits=10)}",
                
                # Status
                status=random.choice(order_statuses),
                payment_status="paid" if random.random() > 0.1 else "pending",
                payment_method=random.choice(payment_methods),
                
                # Addresses
                billing_name=f"{customer.first_name} {customer.last_name}",
                billing_address=customer.street_address,
                billing_city=customer.city,
                billing_state=customer.state,
                billing_postal=customer.postal_code,
                billing_country=customer.country,
                
                shipping_name=f"{customer.first_name} {customer.last_name}",
                shipping_address=customer.street_address,
                shipping_city=customer.city,
                shipping_state=customer.state,
                shipping_postal=customer.postal_code,
                shipping_country=customer.country,
                
                # Dates
                order_date=order_date,
                shipped_date=order_date + timedelta(days=random.randint(1, 3)) if random.random() > 0.3 else None,
                delivered_date=order_date + timedelta(days=random.randint(4, 7)) if random.random() > 0.4 else None,
                
                # Notes
                customer_notes=fake.sentence() if random.random() > 0.7 else None,
                internal_notes=fake.sentence() if random.random() > 0.8 else None,
                
                created_at=order_date,
                updated_at=datetime.utcnow(),
            )
            
            self.session.add(order)
            self.session.flush()  # Get order ID
            
            # Add order items
            num_items = random.randint(1, 5)
            order_total = 0
            
            for _ in range(num_items):
                product = random.choice(products)
                quantity = random.randint(1, 3)
                price = product.sale_price if product.sale_price else product.price
                
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    product_sku=product.sku,
                    quantity=quantity,
                    price=price,
                    total=price * quantity,
                    created_at=order_date,
                )
                
                self.session.add(order_item)
                order_total += order_item.total
            
            # Update order totals
            order.subtotal = order_total
            order.tax = round(order_total * 0.08, 2)  # 8% tax
            order.shipping = round(random.uniform(5.00, 25.00), 2)
            order.total = order.subtotal + order.tax + order.shipping
            
            if (i + 1) % 20 == 0:
                self.session.flush()
                print(f"Created {i + 1}/{num_orders} orders...")
        
        self.session.flush()
        self._records_affected = num_orders
        print(f"Successfully seeded {num_orders} orders")
    
    def rollback(self):
        """Remove fake orders."""
        from myapp.models import Order, OrderItem
        
        # Delete order items first
        self.session.query(OrderItem).filter(
            OrderItem.order_id.in_(
                self.session.query(Order.id).filter(
                    Order.order_number.like("ORD-%")
                )
            )
        ).delete(synchronize_session=False)
        
        # Delete orders
        deleted = self.session.query(Order).filter(
            Order.order_number.like("ORD-%")
        ).delete(synchronize_session=False)
        
        self.session.flush()
        print(f"Deleted {deleted} fake orders and their items")