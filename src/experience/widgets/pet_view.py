from PySide6.QtWidgets import QWidget, QHBoxLayout, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from src.experience.widgets.centered_label import CenteredLabel
from src.experience.pet_catalog import PET_CATALOG, DEFAULT_PET
from src.experience.sprite_composer import compose_pet_pixmap


# Extra space reserved around the pet body so accessories can render
# without being clipped — and without shrinking the pet to make room.
# Vertical headroom covers tall hats; horizontal side-room covers hats
# that are off-center (e.g. a top hat anchored on the cat's head, which
# isn't centered on the sprite's content rect).
_HAT_HEADROOM_RATIO = 0.5
_HAT_SIDE_ROOM_RATIO = 0.25


class PetView(QWidget):
    """Live preview of the active pet with any equipped accessories.

    The pet body always renders at the same fixed pixel size regardless of
    whether an accessory is equipped — scaling is driven by the pet's own
    native dimensions, not the composed (pet + hat) canvas.  The label is
    given extra headroom above the body so hats extend upward instead of
    squishing the pet.
    """

    def __init__(self, parent=None, size: int = 140):
        super().__init__(parent)
        self._size = size
        self._headroom = int(size * _HAT_HEADROOM_RATIO)
        self._side_room = int(size * _HAT_SIDE_ROOM_RATIO)

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.label = CenteredLabel("")
        # Bottom-align so the pet body always sits at the same y position;
        # the hat extends upward into the headroom above.
        self.label.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)
        self.label.setFixedSize(
            size + 2 * self._side_room,
            size + self._headroom,
        )
        self.layout.addWidget(self.label)

        self.refresh()

        app = QApplication.instance()
        if hasattr(app, "signals"):
            app.signals.pet_appearance_changed.connect(self.refresh)

    def refresh(self):
        from src.intelligence.pet_manager import PetManager

        mgr = PetManager()
        pet_id = mgr.get_active_pet()
        accessories = mgr.get_equipped_accessories()
        pet_info = PET_CATALOG.get(pet_id, PET_CATALOG[DEFAULT_PET])

        # Native pet dimensions drive the scale factor so the pet body is
        # the same size for every pet and every accessory loadout.
        base = QPixmap(pet_info["sprite"])
        if base.isNull():
            self.label.clear()
            return
        base_side = max(base.width(), base.height())
        k = self._size / base_side

        composed = compose_pet_pixmap(pet_id, accessories)
        if composed.isNull():
            composed = base

        scaled = composed.scaled(
            int(composed.width() * k),
            int(composed.height() * k),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.label.setPixmap(scaled)


class CompactPetView(PetView):
    """Smaller `PetView` variant used on the Virtual Pet page.

    Inherits the same rendering logic as `PetView` but defaults to a
    smaller body size so the full page (preview + catalog + accessories)
    fits within the main window without scrolling.
    """

    def __init__(self, parent=None, size: int = 110):
        super().__init__(parent, size=size)
