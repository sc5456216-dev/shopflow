# ShopFlow

A full-stack e-commerce app: browse products, search and filter, add to a cart, check out, and manage orders.

**Stack:** Django, Django REST Framework, JWT (SimpleJWT), PostgreSQL (SQLite for quick local runs), vanilla JavaScript front end, Docker Compose.

## Features
- Public product catalogue with search and category filter
- Register and log in with JWT authentication
- Shopping cart with stock validation (adding the same product merges quantities)
- Checkout inside a database transaction: locks product rows, decrements stock, creates the order, clears the cart
- Order history, demo "pay" step, and cancel (restores stock)
- Users only see their own cart and orders
- Django admin for managing products, categories, and orders
- Automated API tests

## Run locally (SQLite)
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_products
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver 8001
```
Open http://127.0.0.1:8001

## Run with Docker (PostgreSQL)
```bash
docker compose up --build
docker compose exec web python manage.py seed_products
```
Open http://localhost:8000

## Run tests
```bash
python manage.py test
```

## API
| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | /api/register/ | Create an account |
| POST | /api/token/ | Get a JWT access token |
| GET | /api/products/?search=&category= | Browse products (public) |
| GET | /api/categories/ | List categories (public) |
| GET, POST | /api/cart/ | View cart or add a product |
| PATCH, DELETE | /api/cart/<id>/ | Change quantity or remove |
| POST | /api/checkout/ | Turn the cart into an order |
| GET | /api/orders/ | Your orders |
| POST | /api/orders/<id>/pay/ | Mark a pending order paid (demo) |
| POST | /api/orders/<id>/cancel/ | Cancel a pending order and restore stock |

Payments are simulated. A real payment provider (for example Stripe) is not connected.

## Ideas to extend
- React or Tailwind front end
- Product images and reviews
- A real payment gateway
- Deploy to Render or Railway
