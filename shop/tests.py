from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import CartItem, Category, Order, Product


class ShopApiTests(APITestCase):
    def setUp(self):
        category = Category.objects.create(name="Books")
        self.book = Product.objects.create(
            name="Python Book", price="100.00", stock=5, category=category
        )
        self.pen = Product.objects.create(name="Pen", price="10.00", stock=2)

    def login(self, username="sam"):
        if not User.objects.filter(username=username).exists():
            User.objects.create_user(username, password="strongpass1")
        token = self.client.post(
            "/api/token/", {"username": username, "password": "strongpass1"}
        ).json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def add_to_cart(self, product, quantity=1):
        return self.client.post("/api/cart/", {"product_id": product.id, "quantity": quantity})

    def test_register(self):
        res = self.client.post("/api/register/", {"username": "new", "password": "strongpass1"})
        self.assertEqual(res.status_code, 201)

    def test_products_are_public_and_searchable(self):
        self.assertEqual(len(self.client.get("/api/products/").json()), 2)
        found = self.client.get("/api/products/?search=python").json()
        self.assertEqual([p["name"] for p in found], ["Python Book"])
        by_category = self.client.get(f"/api/products/?category={self.book.category_id}").json()
        self.assertEqual(len(by_category), 1)

    def test_cart_requires_login(self):
        self.assertEqual(self.client.get("/api/cart/").status_code, 401)

    def test_adding_twice_merges_and_respects_stock(self):
        self.login()
        self.add_to_cart(self.pen, 1)
        self.add_to_cart(self.pen, 1)
        self.assertEqual(CartItem.objects.get().quantity, 2)
        res = self.add_to_cart(self.pen, 1)
        self.assertEqual(res.status_code, 400)

    def test_checkout_reduces_stock_and_clears_cart(self):
        self.login()
        self.add_to_cart(self.book, 2)
        self.add_to_cart(self.pen, 1)
        res = self.client.post("/api/checkout/", {"shipping_address": "Kathmandu, Nepal"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["total"], "210.00")
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 3)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_checkout_with_empty_cart_fails(self):
        self.login()
        res = self.client.post("/api/checkout/", {"shipping_address": "Kathmandu, Nepal"})
        self.assertEqual(res.status_code, 400)

    def test_cancel_restores_stock_and_pay_blocks_cancel(self):
        self.login()
        self.add_to_cart(self.book, 2)
        order_id = self.client.post("/api/checkout/", {"shipping_address": "Kathmandu"}).json()["id"]
        self.client.post(f"/api/orders/{order_id}/cancel/")
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 5)
        self.assertEqual(Order.objects.get().status, "cancelled")

        self.add_to_cart(self.book, 1)
        order_id = self.client.post("/api/checkout/", {"shipping_address": "Kathmandu"}).json()["id"]
        self.client.post(f"/api/orders/{order_id}/pay/")
        res = self.client.post(f"/api/orders/{order_id}/cancel/")
        self.assertEqual(res.status_code, 400)

    def test_users_cannot_see_each_others_orders(self):
        self.login("alice")
        self.add_to_cart(self.pen, 1)
        self.client.post("/api/checkout/", {"shipping_address": "Kathmandu"})
        self.login("bob")
        self.assertEqual(self.client.get("/api/orders/").json(), [])
