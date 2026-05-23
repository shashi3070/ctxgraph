from __future__ import annotations

from typing import Any, Dict, List

from complex_app.inventory.models import Warehouse
from complex_app.inventory.service import InventoryService
from complex_app.shared.cache import Cache
from complex_app.shared.database import Database
from complex_app.shared.errors import ValidationError


class WarehouseManager:
    def __init__(
        self,
        db: Database,
        cache: Cache,
        inventory_service: InventoryService,
    ) -> None:
        self._db = db
        self._cache = cache
        self._inventory_service = inventory_service

    def transfer_stock(
        self,
        from_warehouse_id: str,
        to_warehouse_id: str,
        product_id: str,
        quantity: int,
    ) -> None:
        if quantity <= 0:
            raise ValidationError(
                code="invalid_quantity",
                message="Transfer quantity must be positive",
            )

        if from_warehouse_id == to_warehouse_id:
            raise ValidationError(
                code="same_warehouse",
                message="Source and destination warehouses must be different",
            )

        released = self._inventory_service.release_stock(
            product_id=product_id,
            warehouse_id=from_warehouse_id,
            quantity=quantity,
        )
        if released is not None:
            return

        rows = self._db.fetch_all(
            "SELECT * FROM stock_items WHERE product_id = :product_id AND warehouse_id = :warehouse_id",
            {"product_id": product_id, "warehouse_id": to_warehouse_id},
        )

        if rows:
            target = rows[0]
            target_qty = target.get("quantity", 0) + quantity
            self._db.execute(
                "UPDATE stock_items SET quantity = :quantity, updated_at = :updated_at WHERE id = :id",
                {
                    "id": target["id"],
                    "quantity": target_qty,
                    "updated_at": target.get("updated_at", ""),
                },
            )
        else:
            from complex_app.inventory.models import StockItem

            item = StockItem(
                product_id=product_id,
                warehouse_id=to_warehouse_id,
                quantity=quantity,
            )
            self._db.execute(
                "INSERT INTO stock_items (id, product_id, warehouse_id, quantity, reserved_quantity, reorder_point, reorder_quantity, created_at, updated_at) VALUES (:id, :product_id, :warehouse_id, :quantity, :reserved_quantity, :reorder_point, :reorder_quantity, :created_at, :updated_at)",
                item.to_dict(),
            )

        self._cache.delete(f"stock:{product_id}:{from_warehouse_id}")
        self._cache.delete(f"stock:{product_id}:{to_warehouse_id}")
        self._cache.delete(f"stock:{product_id}")

    def get_warehouse_capacity(self, warehouse_id: str) -> Dict[str, Any]:
        cached = self._cache.get(f"warehouse_capacity:{warehouse_id}")
        if cached is not None:
            return cached

        rows = self._db.fetch_all(
            "SELECT * FROM warehouses WHERE id = :id",
            {"id": warehouse_id},
        )
        if not rows:
            raise ValidationError(
                code="warehouse_not_found",
                message="Warehouse not found",
            )

        w = Warehouse.from_dict(rows[0])
        result = {
            "warehouse_id": w.id,
            "name": w.name,
            "capacity": w.capacity,
            "used_capacity": w.used_capacity,
            "available_capacity": w.capacity - w.used_capacity,
            "utilization_pct": (
                round((w.used_capacity / w.capacity) * 100, 2)
                if w.capacity > 0
                else 0.0
            ),
        }
        self._cache.set(
            f"warehouse_capacity:{warehouse_id}", result
        )
        return result

    def get_all_warehouses(self) -> List[Warehouse]:
        rows = self._db.fetch_all("SELECT * FROM warehouses")
        return [Warehouse.from_dict(row) for row in rows]
