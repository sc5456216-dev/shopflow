from django.core.management.base import BaseCommand

from shop.models import Category, Product

SAMPLE = {
    "Electronics": [
        ("Wireless Earbuds", "Bluetooth earbuds with charging case.", "2499.00", 25),
        ("Power Bank 10000mAh", "Fast-charging portable battery.", "1599.00", 40),
        ("USB-C Cable", "1 metre braided cable.", "399.00", 100),
    ],
    "Books": [
        ("Python Crash Course", "Hands-on introduction to Python.", "1899.00", 15),
        ("Clean Code", "A handbook of agile software craftsmanship.", "2199.00", 10),
    ],
    "Accessories": [
        ("Laptop Sleeve 14 inch", "Water-resistant padded sleeve.", "999.00", 30),
        ("Desk Mat", "Large non-slip desk mat.", "1299.00", 20),
        ("Notebook Pack (3)", "A5 ruled notebooks.", "450.00", 60),
    ],
}


class Command(BaseCommand):
    help = "Add sample categories and products"

    def handle(self, *args, **options):
        created = 0
        for category_name, products in SAMPLE.items():
            category, _ = Category.objects.get_or_create(name=category_name)
            for name, description, price, stock in products:
                _, was_created = Product.objects.get_or_create(
                    name=name,
                    defaults={
                        "category": category,
                        "description": description,
                        "price": price,
                        "stock": stock,
                    },
                )
                created += was_created
        self.stdout.write(self.style.SUCCESS(f"Added {created} new products."))
