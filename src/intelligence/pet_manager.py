from datetime import datetime, timezone

from src.intelligence.database import get_database
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
