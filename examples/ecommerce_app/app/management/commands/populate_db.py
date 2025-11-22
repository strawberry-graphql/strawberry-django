import sys
from datetime import datetime, timedelta, timezone

from app.product.models import Brand, Product
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Populate database with sample data"

    @transaction.atomic
    def handle(self, *args, **options):
        # Create superuser
        if not User.objects.filter(username="admin").exists():
            admin = User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="admin",  # nosec B106  # gitleaks:allow
                first_name="Admin",
                last_name="User",
            )
            sys.stdout.write(f"* Created admin user: {admin.username}\n")

        # Create test user
        if not User.objects.filter(username="testuser").exists():
            user = User.objects.create_user(
                username="testuser",
                email="test@example.com",
                password="test123",  # nosec B106  # gitleaks:allow
                first_name="Test",
                last_name="User",
                birth_date=datetime.now(tz=timezone.utc).date()
                - timedelta(days=365 * 25),
            )
            sys.stdout.write(f"* Created test user: {user.username}\n")

        # Create brands
        brands_data = ["Apple", "Samsung", "Google", "Microsoft", "Sony"]
        brands = {}
        for brand_name in brands_data:
            brand, created = Brand.objects.get_or_create(name=brand_name)
            brands[brand_name] = brand
            if created:
                sys.stdout.write(f"* Created brand: {brand.name}\n")

        # Create products
        products_data = [
            {
                "name": "iPhone 15 Pro",
                "brand": "Apple",
                "kind": "physical",
                "description": "Latest iPhone with advanced camera system",
                "price": 999.99,
            },
            {
                "name": "MacBook Pro 16",
                "brand": "Apple",
                "kind": "physical",
                "description": "Professional laptop with M3 chip",
                "price": 2499.99,
            },
            {
                "name": "Samsung Galaxy S24",
                "brand": "Samsung",
                "kind": "physical",
                "description": "Flagship Android smartphone",
                "price": 899.99,
            },
            {
                "name": "Google Pixel 8 Pro",
                "brand": "Google",
                "kind": "physical",
                "description": "Best Android camera phone",
                "price": 799.99,
            },
            {
                "name": "Microsoft Surface Pro 9",
                "brand": "Microsoft",
                "kind": "physical",
                "description": "2-in-1 tablet and laptop",
                "price": 1299.99,
            },
            {
                "name": "Sony WH-1000XM5",
                "brand": "Sony",
                "kind": "physical",
                "description": "Premium noise-cancelling headphones",
                "price": 399.99,
            },
            {
                "name": "Microsoft 365",
                "brand": "Microsoft",
                "kind": "virtual",
                "description": "Productivity suite subscription",
                "price": 99.99,
            },
            {
                "name": "Adobe Creative Cloud",
                "brand": "Adobe",
                "kind": "virtual",
                "description": "Complete creative software suite",
                "price": 54.99,
            },
        ]

        for product_data in products_data:
            brand_name = product_data.pop("brand")
            product, created = Product.objects.get_or_create(
                name=product_data["name"],
                defaults={
                    **product_data,
                    "brand": brands[brand_name],
                },
            )
            if created:
                sys.stdout.write(f"* Created product: {product.name}\n")

        sys.stdout.write(self.style.SUCCESS("\n✓ Database populated successfully!\n"))
        sys.stdout.write("\nYou can now login with:\n")
        sys.stdout.write("  Username: admin\n")
        sys.stdout.write("  Password: admin\n\n")  # gitleaks:allow
        sys.stdout.write("Or use test user:\n")
        sys.stdout.write("  Username: testuser\n")
        sys.stdout.write("  Password: test123\n")  # gitleaks:allow
