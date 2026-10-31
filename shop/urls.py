from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView

from .views import (
    CartViewSet,
    CategoryViewSet,
    CheckoutView,
    OrderViewSet,
    ProductViewSet,
    RegisterView,
)

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")
router.register("cart", CartViewSet, basename="cart")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("token/", TokenObtainPairView.as_view()),
    path("checkout/", CheckoutView.as_view()),
    path("", include(router.urls)),
]
