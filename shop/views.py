from django.contrib.auth.models import User  # noqa: F401
from django.db import transaction
from django.db.models import Q
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CartItem, Category, Order, OrderItem, Product
from .serializers import (
    CartItemSerializer,
    CategorySerializer,
    CheckoutSerializer,
    OrderSerializer,
    ProductSerializer,
    RegisterSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related("category")
        search = self.request.query_params.get("search")
        category = self.request.query_params.get("category")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        if category:
            queryset = queryset.filter(category_id=category)
        return queryset


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user).select_related(
            "product", "product__category"
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]
        item = CartItem.objects.filter(user=request.user, product=product).first()
        new_quantity = (item.quantity if item else 0) + quantity
        if new_quantity > product.stock:
            raise ValidationError({"quantity": f"Only {product.stock} in stock."})
        if item:
            item.quantity = new_quantity
            item.save(update_fields=["quantity"])
        else:
            item = CartItem.objects.create(user=request.user, product=product, quantity=new_quantity)
        return Response(self.get_serializer(item).data, status=201)

    def perform_update(self, serializer):
        quantity = serializer.validated_data.get("quantity")
        if quantity and quantity > serializer.instance.product.stock:
            raise ValidationError({"quantity": f"Only {serializer.instance.product.stock} in stock."})
        serializer.save()


class CheckoutView(APIView):
    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = list(CartItem.objects.filter(user=request.user))
        if not cart:
            raise ValidationError({"detail": "Your cart is empty."})
        products = {
            p.id: p
            for p in Product.objects.select_for_update().filter(
                id__in=[item.product_id for item in cart]
            )
        }
        order = Order.objects.create(
            user=request.user, shipping_address=serializer.validated_data["shipping_address"]
        )
        total = 0
        for item in cart:
            product = products[item.product_id]
            if not product.is_active or item.quantity > product.stock:
                raise ValidationError({"detail": f"Not enough stock for {product.name}."})
            product.stock -= item.quantity
            product.save(update_fields=["stock"])
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                unit_price=product.price,
                quantity=item.quantity,
            )
            total += product.price * item.quantity
        order.total = total
        order.save(update_fields=["total"])
        CartItem.objects.filter(user=request.user).delete()
        return Response(OrderSerializer(order).data, status=201)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        order = self.get_object()
        if order.status != Order.Status.PENDING:
            raise ValidationError({"detail": "Only pending orders can be paid."})
        order.status = Order.Status.PAID  # demo only: no real payment provider
        order.save(update_fields=["status"])
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status != Order.Status.PENDING:
            raise ValidationError({"detail": "Only pending orders can be cancelled."})
        for item in order.items.select_related("product"):
            if item.product:
                item.product.stock += item.quantity
                item.product.save(update_fields=["stock"])
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status"])
        return Response(self.get_serializer(order).data)
