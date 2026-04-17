import json
from datetime import datetime, timezone

from src.intelligence.database import get_database
from src.experience.accessory_catalog import ACCESSORY_CATALOG
from src.experience.pet_catalog import PET_CATALOG, DEFAULT_PET


class PetManager:
    def __init__(self):
        self.db = get_database()

    # ── Queries ──────────────────────────────────────────────

    def get_active_pet(self) -> str:
        cursor = self.db.cursor()
        cursor.execute("SELECT current_pet FROM user_stats WHERE id = 1")
        pet_id = cursor.fetchone()["current_pet"]
        return pet_id if pet_id in PET_CATALOG else DEFAULT_PET

    def get_active_pet_name(self) -> str:
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT i.name FROM user_stats u
            JOIN inventory i ON u.current_pet = i.item_id
            WHERE u.id = 1 AND i.item_type = 'pet'
        """)
        row = cursor.fetchone()
        if row and row["name"]:
            return row["name"]
        return PET_CATALOG.get(DEFAULT_PET, {}).get("name", "")

    def get_pet_name(self, pet_id: str) -> str:
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT name FROM inventory WHERE item_type = 'pet' AND item_id = ?",
            (pet_id,)
        )
        row = cursor.fetchone()
        if row and row["name"]:
            return row["name"]
        return PET_CATALOG.get(pet_id, {}).get("name", pet_id)

    def get_owned_pets(self) -> list[str]:
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT item_id FROM inventory WHERE item_type = 'pet'"
        )
        return [row["item_id"] for row in cursor.fetchall()]

    def get_owned_pet_details(self) -> list[dict]:
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT id, item_id, name FROM inventory WHERE item_type = 'pet'"
        )
        return [{"id": row["id"], "item_id": row["item_id"], "name": row["name"]} for row in cursor.fetchall()]

    def owns_pet(self, pet_id: str) -> bool:
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT 1 FROM inventory WHERE item_type = 'pet' AND item_id = ?",
            (pet_id,),
        )
        return cursor.fetchone() is not None

    def get_coins(self) -> int:
        cursor = self.db.cursor()
        cursor.execute("SELECT coins FROM user_stats WHERE id = 1")
        return cursor.fetchone()["coins"]

    # ── Mutations ────────────────────────────────────────────

    def set_active_pet(self, pet_id: str) -> bool:
        if pet_id not in PET_CATALOG or not self.owns_pet(pet_id):
            return False
        cursor = self.db.cursor()
        cursor.execute(
            "UPDATE user_stats SET current_pet = ? WHERE id = 1", (pet_id,)
        )
        self.db.commit()
        return True

    def rename_pet(self, pet_id: str, name: str) -> bool:
        """Replace the stored custom name for ``pet_id``.

        Returns True when the inventory row's ``name`` column was updated
        and False when the pet isn't owned or ``name`` is blank.  Whitespace
        is stripped and long names are capped to keep UI labels from
        overflowing their cards.
        """
        if not name:
            return False
        trimmed = name.strip()[:32]
        if not trimmed:
            return False
        if pet_id not in PET_CATALOG or not self.owns_pet(pet_id):
            return False

        cursor = self.db.cursor()
        try:
            cursor.execute(
                "UPDATE inventory SET name = ? "
                "WHERE item_type = 'pet' AND item_id = ?",
                (trimmed, pet_id),
            )
            self.db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error renaming pet: {e}")
            self.db.rollback()
            return False

    def purchase_pet(self, pet_id: str, name: str = None) -> bool:
        pet = PET_CATALOG.get(pet_id)
        if pet is None:
            return False

        if name is None:
            name = pet["name"]

        cursor = self.db.cursor()
        try:
            if not self.owns_pet(pet_id):
                coins = self.get_coins()
                if coins < pet["cost"]:
                    return False

                cursor.execute(
                    "UPDATE user_stats SET coins = coins - ? WHERE id = 1",
                    (pet["cost"],),
                )
                cursor.execute(
                    "INSERT INTO inventory (item_type, item_id, name, acquired_at) "
                    "VALUES ('pet', ?, ?, ?)",
                    (pet_id, name, datetime.now(timezone.utc).isoformat()),
                )
            else:
                # Update name if already owns
                cursor.execute(
                    "UPDATE inventory SET name = ? WHERE item_type = 'pet' AND item_id = ?",
                    (name, pet_id),
                )
            self.db.commit()
            return True
        except Exception as e:
            print(f"Error purchasing pet: {e}")
            self.db.rollback()
            return False

    # ── Accessories ──────────────────────────────────────────
    #
    # Accessories are stored in two places:
    #   * `inventory` rows with item_type = 'accessory' record ownership.
    #   * `user_stats.equipped_accessories` (a JSON list of ids) records
    #     what is currently being worn.
    #
    # Equipping rule: one item per slot.  Equipping a new hat automatically
    # removes any other hat from the equipped list so the two can never be
    # drawn on top of each other.

    def get_owned_accessories(self) -> list[str]:
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT item_id FROM inventory WHERE item_type = 'accessory'"
        )
        return [row["item_id"] for row in cursor.fetchall()]

    def owns_accessory(self, accessory_id: str) -> bool:
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT 1 FROM inventory WHERE item_type = 'accessory' AND item_id = ?",
            (accessory_id,),
        )
        return cursor.fetchone() is not None

    def get_equipped_accessories(self) -> list[str]:
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT equipped_accessories FROM user_stats WHERE id = 1"
        )
        row = cursor.fetchone()
        raw = row["equipped_accessories"] if row else None
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return []
        return [aid for aid in data if aid in ACCESSORY_CATALOG]

    def is_accessory_equipped(self, accessory_id: str) -> bool:
        return accessory_id in self.get_equipped_accessories()

    def purchase_accessory(self, accessory_id: str) -> bool:
        accessory = ACCESSORY_CATALOG.get(accessory_id)
        if accessory is None or self.owns_accessory(accessory_id):
            return False

        cost = int(accessory.get("cost", 0))
        if self.get_coins() < cost:
            return False

        cursor = self.db.cursor()
        try:
            cursor.execute(
                "UPDATE user_stats SET coins = coins - ? WHERE id = 1",
                (cost,),
            )
            cursor.execute(
                "INSERT INTO inventory (item_type, item_id, name, acquired_at) "
                "VALUES ('accessory', ?, ?, ?)",
                (
                    accessory_id,
                    accessory["name"],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self.db.commit()
            return True
        except Exception as e:
            print(f"Error purchasing accessory: {e}")
            self.db.rollback()
            return False

    def equip_accessory(self, accessory_id: str) -> bool:
        accessory = ACCESSORY_CATALOG.get(accessory_id)
        if accessory is None or not self.owns_accessory(accessory_id):
            return False

        slot = accessory.get("slot")
        current = [
            aid for aid in self.get_equipped_accessories()
            if ACCESSORY_CATALOG.get(aid, {}).get("slot") != slot
        ]
        current.append(accessory_id)
        return self._save_equipped_accessories(current)

    def unequip_accessory(self, accessory_id: str) -> bool:
        current = self.get_equipped_accessories()
        if accessory_id not in current:
            return False
        current.remove(accessory_id)
        return self._save_equipped_accessories(current)

    def toggle_accessory(self, accessory_id: str) -> bool:
        if self.is_accessory_equipped(accessory_id):
            return self.unequip_accessory(accessory_id)
        return self.equip_accessory(accessory_id)

    def _save_equipped_accessories(self, accessories: list[str]) -> bool:
        cursor = self.db.cursor()
        cursor.execute(
            "UPDATE user_stats SET equipped_accessories = ? WHERE id = 1",
            (json.dumps(accessories),),
        )
        self.db.commit()
        return True
