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

    def get_owned_pets(self) -> list[str]:
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT item_id FROM inventory WHERE item_type = 'pet'"
        )
        return [row["item_id"] for row in cursor.fetchall()]

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

    def purchase_pet(self, pet_id: str) -> bool:
        pet = PET_CATALOG.get(pet_id)
        if pet is None or self.owns_pet(pet_id):
            return False

        coins = self.get_coins()
        if coins < pet["cost"]:
            return False

        cursor = self.db.cursor()
        cursor.execute(
            "UPDATE user_stats SET coins = coins - ? WHERE id = 1",
            (pet["cost"],),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO inventory (item_type, item_id, acquired_at) "
            "VALUES ('pet', ?, ?)",
            (pet_id, datetime.now(timezone.utc).isoformat()),
        )
        self.db.commit()
        return True
