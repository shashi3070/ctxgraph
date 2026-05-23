from __future__ import annotations

from typing import Any, Dict, List, Optional

from complex_app.auth.models import Permission, User
from complex_app.auth.service import AuthService
from complex_app.inventory.models import (
    InventoryTransaction,
    Product,
    StockItem,
    TransactionType,
    Warehouse,
)
from complex_app.notifications.service import NotificationService
from complex_app.shared.base import BaseService
from complex_app.shared.cache import Cache
from complex_app.shared.config import get_config
from complex_app.shared.database import Database, get_database
from complex_app.shared.errors import NotFoundError, ValidationError


class InventoryService(BaseService):
    def __init__(
        self,
        db: Database,
        cache: Cache,
        auth_service: AuthService,
        notification_service: NotificationService,
    ) -> None:
        self._db = db
        self._cache = cache
        self._auth_service = auth_service
        self._notification_service = notification_service

    def _validate(self, user: Optional[User] = None) -> None:
        if user is not None and not user.is_active:
            raise ValidationError(
                code="inactive_user", message="User account is inactive"
            )

    def _authorize(self, user: Optional[User] = None) -> None:
        if user is None:
            raise ValidationError(
                code="not_authenticated",
                message="Authentication required",
            )

    def create_product(self, user_id: str, data: Dict[str, Any]) -> Product:
        user = self._auth_service.get_user(user_id)
        self._validate(user)
        if not self._auth_service.has_permission(user, Permission.WRITE):
            raise ValidationError(
                code="access_denied",
                message="User does not have WRITE permission",
            )

        product = Product(**data)
        self._db.execute(
            "INSERT INTO products (id, name, slug, description, price, currency, category_id, tags, attributes, is_active, image_urls, created_at, updated_at) VALUES (:id, :name, :slug, :description, :price, :currency, :category_id, :tags, :attributes, :is_active, :image_urls, :created_at, :updated_at)",
            product.to_dict(),
        )
        return product

    def get_product(self, product_id: str) -> Product:
        cached = self._cache.get(f"product:{product_id}")
        if cached is not None:
            return Product.from_dict(cached)

        rows = self._db.fetch_all(
            "SELECT * FROM products WHERE id = :id", {"id": product_id}
        )
        if not rows:
            raise NotFoundError(
                code="product_not_found", message="Product not found"
            )

        product = Product.from_dict(rows[0])
        self._cache.set(f"product:{product_id}", product.to_dict())
        return product

    def update_product(
        self, user_id: str, product_id: str, data: Dict[str, Any]
    ) -> Product:
        user = self._auth_service.get_user(user_id)
        self._validate(user)
        if not self._auth_service.has_permission(user, Permission.WRITE):
            raise ValidationError(
                code="access_denied",
                message="User does not have WRITE permission",
            )

        rows = self._db.fetch_all(
            "SELECT * FROM products WHERE id = :id", {"id": product_id}
        )
        if not rows:
            raise NotFoundError(
                code="product_not_found", message="Product not found"
            )

        product = Product.from_dict(rows[0])
        for key, value in data.items():
            if hasattr(product, key):
                setattr(product, key, value)

        self._db.execute(
            "UPDATE products SET name = :name, slug = :slug, description = :description, price = :price, currency = :currency, category_id = :category_id, tags = :tags, attributes = :attributes, is_active = :is_active, image_urls = :image_urls, updated_at = :updated_at WHERE id = :id",
            product.to_dict(),
        )
        self._cache.delete(f"product:{product_id}")
        return product

    def check_stock(
        self, product_id: str, warehouse_id: Optional[str] = None
    ) -> int:
        cache_key = (
            f"stock:{product_id}:{warehouse_id}"
            if warehouse_id
            else f"stock:{product_id}"
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if warehouse_id:
            rows = self._db.fetch_all(
                "SELECT * FROM stock_items WHERE product_id = :product_id AND warehouse_id = :warehouse_id",
                {"product_id": product_id, "warehouse_id": warehouse_id},
            )
        else:
            rows = self._db.fetch_all(
                "SELECT * FROM stock_items WHERE product_id = :product_id",
                {"product_id": product_id},
            )

        total = sum(
            row.get("quantity", 0) - row.get("reserved_quantity", 0)
            for row in rows
        )
        self._cache.set(cache_key, total)
        return total

    def reserve_stock(
        self, product_id: str, warehouse_id: str, quantity: int
    ) -> bool:
        config = get_config()
        if quantity <= 0:
            raise ValidationError(
                code="invalid_quantity",
                message="Quantity must be positive",
            )

        rows = self._db.fetch_all(
            "SELECT * FROM stock_items WHERE product_id = :product_id AND warehouse_id = :warehouse_id",
            {"product_id": product_id, "warehouse_id": warehouse_id},
        )
        if not rows:
            raise NotFoundError(
                code="stock_item_not_found",
                message="Stock item not found",
            )

        item = StockItem.from_dict(rows[0])
        available = item.quantity - item.reserved_quantity
        if available < quantity:
            return False

        item.reserved_quantity += quantity
        self._db.execute(
            "UPDATE stock_items SET reserved_quantity = :reserved_quantity, updated_at = :updated_at WHERE id = :id",
            item.to_dict(),
        )

        self._cache.delete(
            f"stock:{product_id}:{warehouse_id}"
        )
        self._cache.delete(f"stock:{product_id}")

        transaction = InventoryTransaction(
            product_id=product_id,
            warehouse_id=warehouse_id,
            type=TransactionType.OUT,
            quantity=quantity,
            reference=f"reserve:{product_id}:{warehouse_id}",
            user_id="system",
        )

        db = get_database()
        db.execute(
            "INSERT INTO inventory_transactions (product_id, warehouse_id, type, quantity, reference, user_id) VALUES (:product_id, :warehouse_id, :type, :quantity, :reference, :user_id)",
            {
                "product_id": transaction.product_id,
                "warehouse_id": transaction.warehouse_id,
                "type": transaction.type.value,
                "quantity": transaction.quantity,
                "reference": transaction.reference,
                "user_id": transaction.user_id,
            },
        )

        return True

    def release_stock(
        self, product_id: str, warehouse_id: str, quantity: int
    ) -> None:
        if quantity <= 0:
            raise ValidationError(
                code="invalid_quantity",
                message="Quantity must be positive",
            )

        rows = self._db.fetch_all(
            "SELECT * FROM stock_items WHERE product_id = :product_id AND warehouse_id = :warehouse_id",
            {"product_id": product_id, "warehouse_id": warehouse_id},
        )
        if not rows:
            raise NotFoundError(
                code="stock_item_not_found",
                message="Stock item not found",
            )

        item = StockItem.from_dict(rows[0])
        item.reserved_quantity = max(0, item.reserved_quantity - quantity)
        self._db.execute(
            "UPDATE stock_items SET reserved_quantity = :reserved_quantity, updated_at = :updated_at WHERE id = :id",
            item.to_dict(),
        )

        self._cache.delete(
            f"stock:{product_id}:{warehouse_id}"
        )
        self._cache.delete(f"stock:{product_id}")

        transaction = InventoryTransaction(
            product_id=product_id,
            warehouse_id=warehouse_id,
            type=TransactionType.IN,
            quantity=quantity,
            reference=f"release:{product_id}:{warehouse_id}",
            user_id="system",
        )

        db = get_database()
        db.execute(
            "INSERT INTO inventory_transactions (product_id, warehouse_id, type, quantity, reference, user_id) VALUES (:product_id, :warehouse_id, :type, :quantity, :reference, :user_id)",
            {
                "product_id": transaction.product_id,
                "warehouse_id": transaction.warehouse_id,
                "type": transaction.type.value,
                "quantity": transaction.quantity,
                "reference": transaction.reference,
                "user_id": transaction.user_id,
            },
        )

    def reorder_stock(self, warehouse_id: str) -> None:
        rows = self._db.fetch_all(
            "SELECT * FROM stock_items WHERE warehouse_id = :warehouse_id",
            {"warehouse_id": warehouse_id},
        )

        low_stock_items: List[StockItem] = []
        for row in rows:
            item = StockItem.from_dict(row)
            if item.quantity <= item.reorder_point:
                low_stock_items.append(item)

        for item in low_stock_items:
            item.quantity += item.reorder_quantity
            self._db.execute(
                "UPDATE stock_items SET quantity = :quantity, updated_at = :updated_at WHERE id = :id",
                item.to_dict(),
            )

            transaction = InventoryTransaction(
                product_id=item.product_id,
                warehouse_id=warehouse_id,
                type=TransactionType.IN,
                quantity=item.reorder_quantity,
                reference=f"reorder:{warehouse_id}",
                user_id="system",
            )

            db = get_database()
            db.execute(
                "INSERT INTO inventory_transactions (product_id, warehouse_id, type, quantity, reference, user_id) VALUES (:product_id, :warehouse_id, :type, :quantity, :reference, :user_id)",
                {
                    "product_id": transaction.product_id,
                    "warehouse_id": transaction.warehouse_id,
                    "type": transaction.type.value,
                    "quantity": transaction.quantity,
                    "reference": transaction.reference,
                    "user_id": transaction.user_id,
                },
            )

            self._cache.delete(
                f"stock:{item.product_id}:{warehouse_id}"
            )
            self._cache.delete(f"stock:{item.product_id}")

            self._notification_service.send_low_stock_alert(
                warehouse_id=warehouse_id,
                product_id=item.product_id,
                current_quantity=item.quantity,
                reorder_point=item.reorder_point,
            )

    def list_products(
        self,
        category_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> List[Product]:
        query = "SELECT * FROM products WHERE 1=1"
        params: Dict[str, Any] = {}

        if category_id is not None:
            query += " AND category_id = :category_id"
            params["category_id"] = category_id

        if tags:
            for i, tag in enumerate(tags):
                param = f"tag_{i}"
                query += f" AND tags LIKE :{param}"
                params[param] = f"%{tag}%"

        query += " LIMIT :limit OFFSET :offset"
        params["limit"] = per_page
        params["offset"] = (page - 1) * per_page

        rows = self._db.fetch_all(query, params)
        return [Product.from_dict(row) for row in rows]
