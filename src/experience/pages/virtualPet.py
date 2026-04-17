from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QApplication,
    QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt

from src.experience.widgets.centered_label import CenteredLabel
from src.experience.widgets.pet_view import PetView
from src.experience.widgets.pet_card import PetCard
from src.experience.pet_catalog import PET_CATALOG
from src.intelligence.pet_manager import PetManager


class VirtualPet(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.mgr = PetManager()

        root = QVBoxLayout()
        root.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(12)
        self.setLayout(root)

        # ── Title ────────────────────────────────────────────
        title = CenteredLabel("Virtual Pet")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        root.addWidget(title)

        # ── Live preview ─────────────────────────────────────
        self.pet_view = PetView(self, size=150)
        root.addWidget(self.pet_view, alignment=Qt.AlignCenter)

        self.pet_name_label = CenteredLabel()
        self.pet_name_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        root.addWidget(self.pet_name_label)

        root.addSpacing(8)

        # ── Section header ───────────────────────────────────
        header_row = QHBoxLayout()
        section_label = QLabel("Choose Your Pet")
        section_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        header_row.addWidget(section_label)

        header_row.addStretch()

        self.coins_label = QLabel()
        self.coins_label.setObjectName("coinLabel")
        self.coins_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        header_row.addWidget(self.coins_label)

        root.addLayout(header_row)

        # ── Pet card row (scrollable) ────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(200)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.cards_layout.setSpacing(12)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.cards_container.setLayout(self.cards_layout)
        scroll.setWidget(self.cards_container)

        root.addWidget(scroll)

        # ── Build cards ──────────────────────────────────────
        self._cards: dict[str, PetCard] = {}
        for pet_id, info in PET_CATALOG.items():
            custom_name = self.mgr.get_pet_name(pet_id)
            card = PetCard(pet_id, custom_name, info["sprite"], self)
            card.clicked.connect(self._on_card_clicked)
            card.purchaseClicked.connect(self._on_purchase_clicked)
            self.cards_layout.addWidget(card)
            self._cards[pet_id] = card

        self.cards_layout.addStretch()

        # ── Status toast ─────────────────────────────────────
        self.toast_label = CenteredLabel("")
        self.toast_label.setStyleSheet("font-size: 12px; min-height: 20px;")
        root.addWidget(self.toast_label)

        root.addStretch()

        self._refresh_state()

    # ── State refresh ────────────────────────────────────────

    def _refresh_state(self):
        active = self.mgr.get_active_pet()
        owned = set(self.mgr.get_owned_pets())
        coins = self.mgr.get_coins()

        self.pet_name_label.setText(self.mgr.get_active_pet_name())
        self.coins_label.setText(f"{coins} coins")

        for pet_id, card in self._cards.items():
            info = PET_CATALOG[pet_id]
            custom_name = self.mgr.get_pet_name(pet_id)
            card.name_label.setText(custom_name)  # Update the card's name label
            card.set_state(
                equipped=(pet_id == active),
                owned=(pet_id in owned),
                cost=info["cost"],
                affordable=(coins >= info["cost"]),
            )

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_state()
        self.pet_view.refresh()

    # ── Interactions ─────────────────────────────────────────

    def _on_card_clicked(self, pet_id: str):
        active = self.mgr.get_active_pet()

        if self.mgr.owns_pet(pet_id):
            if pet_id == active:
                # Rename the active pet
                current_name = self.mgr.get_active_pet_name()
                name, ok = QInputDialog.getText(self, "Rename Your Pet", "Enter a new name for your pet:", text=current_name)
                if ok and name.strip():
                    self.mgr.purchase_pet(pet_id, name.strip())  # This will update the name
                    self._emit_change()
                    self._show_toast(f"Renamed to {name.strip()}!", "#3b7deb")
                return
            else:
                # For owned pets that are not equipped, ask what to do
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Pet Options")
                msg_box.setText(f"What would you like to do with {self.mgr.get_pet_name(pet_id)}?")
                equip_button = msg_box.addButton("Equip", QMessageBox.ButtonRole.AcceptRole)
                rename_button = msg_box.addButton("Rename", QMessageBox.ButtonRole.RejectRole)
                msg_box.setDefaultButton(equip_button)
                msg_box.exec()

                if msg_box.clickedButton() == equip_button:
                    # Equip the pet
                    self.mgr.set_active_pet(pet_id)
                    self._emit_change()
                    self._show_toast(f"Switched to {self.mgr.get_active_pet_name()}!", "#3b7deb")
                elif msg_box.clickedButton() == rename_button:
                    # Rename the pet
                    current_name = self.mgr.get_pet_name(pet_id)
                    name, ok = QInputDialog.getText(self, "Rename Your Pet", f"Enter a new name for {current_name}:", text=current_name)
                    if ok and name.strip():
                        self.mgr.purchase_pet(pet_id, name.strip())  # This will update the name
                        self._emit_change()
                        self._show_toast(f"Renamed to {name.strip()}!", "#3b7deb")
                return

        # If the pet is not owned, instruct the user to press Buy.
        self._show_toast("Use the Buy button to purchase this pet.", "#f5a623")

    def _on_purchase_clicked(self, pet_id: str):
        cost = PET_CATALOG[pet_id]["cost"]
        if self.mgr.get_coins() < cost:
            self._show_toast("Not enough coins!", "#e74c3c")
            return

        default_name = PET_CATALOG[pet_id]["name"]
        name, ok = QInputDialog.getText(self, "Name Your Pet", f"Enter a name for your {default_name}:", text=default_name)
        if not ok or not name.strip():
            return

        if self.mgr.purchase_pet(pet_id, name.strip()):
            self.mgr.set_active_pet(pet_id)
            self._emit_change()
            self._show_toast(f"Purchased and equipped {name.strip()}!", "#27ae60")
        else:
            self._show_toast("Purchase failed!", "#e74c3c")

    def _emit_change(self):
        self._refresh_state()
        self.pet_view.refresh()
        app = QApplication.instance()
        if hasattr(app, "signals"):
            app.signals.pet_appearance_changed.emit()

    def _show_toast(self, text: str, color: str):
        self.toast_label.setText(text)
        self.toast_label.setStyleSheet(
            f"color: {color}; font-size: 12px; min-height: 20px;"
        )
