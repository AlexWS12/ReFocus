from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QApplication,
    QDialog, QPushButton, QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt

from src.experience.widgets.centered_label import CenteredLabel
from src.experience.widgets.pet_view import CompactPetView
from src.experience.widgets.pet_card import PetCard
from src.experience.widgets.accessory_card import AccessoryCard
from src.experience.pet_catalog import PET_CATALOG
from src.experience.accessory_catalog import ACCESSORY_CATALOG
from src.intelligence.pet_manager import PetManager


class PurchaseConfirmDialog(QDialog):
    def __init__(self, pet_name: str, cost: int, current_coins: int, parent=None):
        super().__init__(parent)
        self.setObjectName("confirmDialog")
        self.setWindowTitle("Confirm Purchase")
        self.setModal(True)
        self.setMinimumWidth(360)

        remaining = current_coins - cost

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel("Buy this pet?")
        title.setObjectName("confirmDialogTitle")
        layout.addWidget(title)

        body = QLabel(f"Spend {cost} coins to unlock {pet_name}.")
        body.setObjectName("confirmDialogBody")
        body.setWordWrap(True)
        layout.addWidget(body)

        meta = QLabel(f"Balance after purchase: {remaining} coins")
        meta.setObjectName("confirmDialogMeta")
        layout.addWidget(meta)

        button_row = QHBoxLayout()
        button_row.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("confirmSecondaryButton")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        buy_btn = QPushButton("Buy Pet")
        buy_btn.setObjectName("confirmPrimaryButton")
        buy_btn.clicked.connect(self.accept)
        button_row.addWidget(buy_btn)

        layout.addLayout(button_row)

        # Use cancel as safe default to reduce accidental purchases.
        cancel_btn.setDefault(True)
        cancel_btn.setAutoDefault(True)


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
        self.pet_view = CompactPetView(self)
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

        # ── Pet card row ─────────────────────────────────────
        # Minimum width chosen so all pet cards fit without horizontal
        # scrolling: 4 cards * 140 + 3 gaps * 12 + 8px of content margins.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(200)
        scroll.setMinimumWidth(620)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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

        # ── Accessories section ──────────────────────────────
        # Extra breathing room so the Accessories header is clearly
        # separated from the pet purchase row above it.
        root.addSpacing(48)

        accessories_header = QLabel("Accessories")
        accessories_header.setStyleSheet("font-size: 14px; font-weight: 600;")
        root.addWidget(accessories_header)

        # Minimum width chosen so all accessory cards fit without horizontal
        # scrolling: 4 cards * 120 + 3 gaps * 10 + 8px of content margins.
        acc_scroll = QScrollArea()
        acc_scroll.setWidgetResizable(True)
        acc_scroll.setFixedHeight(185)
        acc_scroll.setMinimumWidth(540)
        acc_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        acc_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        acc_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        self.acc_container = QWidget()
        self.acc_container.setStyleSheet("background: transparent;")
        self.acc_layout = QHBoxLayout()
        self.acc_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.acc_layout.setSpacing(10)
        self.acc_layout.setContentsMargins(4, 4, 4, 4)
        self.acc_container.setLayout(self.acc_layout)
        acc_scroll.setWidget(self.acc_container)
        root.addWidget(acc_scroll)

        self._accessory_cards: dict[str, AccessoryCard] = {}
        for acc_id, info in ACCESSORY_CATALOG.items():
            card = AccessoryCard(acc_id, info["name"], info["sprite"], self)
            card.clicked.connect(self._on_accessory_clicked)
            card.purchaseClicked.connect(self._on_accessory_purchase_clicked)
            self.acc_layout.addWidget(card)
            self._accessory_cards[acc_id] = card

        self.acc_layout.addStretch()

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

        owned_accessories = set(self.mgr.get_owned_accessories())
        equipped_accessories = set(self.mgr.get_equipped_accessories())
        for acc_id, card in self._accessory_cards.items():
            info = ACCESSORY_CATALOG[acc_id]
            cost = int(info.get("cost", 0))
            card.set_state(
                equipped=(acc_id in equipped_accessories),
                owned=(acc_id in owned_accessories),
                cost=cost,
                affordable=(coins >= cost),
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
                # Clicking the equipped pet always means "rename me".
                self._prompt_rename(pet_id)
                return

            # Owned-but-not-equipped pet: let the user pick equip vs rename.
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Pet Options")
            msg_box.setText(
                f"What would you like to do with {self.mgr.get_pet_name(pet_id)}?"
            )
            equip_button = msg_box.addButton("Equip", QMessageBox.ButtonRole.AcceptRole)
            rename_button = msg_box.addButton("Rename", QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(equip_button)
            msg_box.exec()

            if msg_box.clickedButton() == equip_button:
                self.mgr.set_active_pet(pet_id)
                self._emit_change()
                self._show_toast(
                    f"Switched to {self.mgr.get_active_pet_name()}!", "#3b7deb"
                )
            elif msg_box.clickedButton() == rename_button:
                self._prompt_rename(pet_id)
            return

        # If the pet is not owned, instruct the user to press Buy.
        self._show_toast("Use the Buy button to purchase this pet.", "#f5a623")

    def _prompt_rename(self, pet_id: str):
        """Show a rename dialog for ``pet_id`` and persist the new name.

        Updates the stored custom name via ``PetManager.rename_pet`` (not
        ``purchase_pet``), refreshes every surface that shows the pet name
        — the large preview label, the matching pet card, and the floating
        pet window via the ``pet_appearance_changed`` signal — and surfaces
        a confirmation toast.
        """
        current_name = self.mgr.get_pet_name(pet_id)
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Your Pet",
            f"Enter a new name for {current_name}:",
            text=current_name,
        )
        if not ok:
            return

        cleaned = new_name.strip()
        if not cleaned:
            self._show_toast("Name can't be empty.", "#e74c3c")
            return
        if cleaned == current_name:
            return  # nothing to do

        if self.mgr.rename_pet(pet_id, cleaned):
            self._emit_change()
            self._show_toast(f"Renamed to {cleaned}!", "#3b7deb")
        else:
            self._show_toast("Rename failed.", "#e74c3c")

    def _on_purchase_clicked(self, pet_id: str):
        cost = PET_CATALOG[pet_id]["cost"]
        if self.mgr.get_coins() < cost:
            self._show_toast("Not enough coins!", "#e74c3c")
            return

        default_name = PET_CATALOG[pet_id]["name"]
        if not self._confirm_purchase(default_name, cost):
            self._show_toast("Purchase cancelled.", "#8892a4")
            return

        name, ok = QInputDialog.getText(
            self,
            "Name Your Pet",
            f"Enter a name for your {default_name}:",
            text=default_name,
        )
        if not ok:
            self._show_toast("Purchase cancelled.", "#8892a4")
            return

        cleaned_name = name.strip()
        if not cleaned_name:
            self._show_toast("Name can't be empty.", "#e74c3c")
            return

        if self.mgr.purchase_pet(pet_id, cleaned_name):
            self.mgr.set_active_pet(pet_id)
            self._emit_change()
            self._show_toast(f"Purchased and equipped {cleaned_name}!", "#27ae60")
        else:
            self._show_toast("Purchase failed!", "#e74c3c")

    def _on_accessory_clicked(self, accessory_id: str):
        if not self.mgr.owns_accessory(accessory_id):
            self._show_toast("Use the Buy button to purchase this accessory.", "#f5a623")
            return

        if self.mgr.toggle_accessory(accessory_id):
            name = ACCESSORY_CATALOG[accessory_id]["name"]
            if self.mgr.is_accessory_equipped(accessory_id):
                self._show_toast(f"Equipped {name}!", "#3b7deb")
            else:
                self._show_toast(f"Unequipped {name}.", "#8892a4")
            self._emit_change()

    def _on_accessory_purchase_clicked(self, accessory_id: str):
        info = ACCESSORY_CATALOG.get(accessory_id)
        if info is None:
            return
        cost = int(info.get("cost", 0))
        if self.mgr.get_coins() < cost:
            self._show_toast("Not enough coins!", "#e74c3c")
            return

        if self.mgr.purchase_accessory(accessory_id):
            self.mgr.equip_accessory(accessory_id)
            self._emit_change()
            self._show_toast(f"Purchased and equipped {info['name']}!", "#27ae60")
        else:
            self._show_toast("Purchase failed!", "#e74c3c")

    def _emit_change(self):
        self._refresh_state()
        self.pet_view.refresh()
        app = QApplication.instance()
        if hasattr(app, "signals"):
            app.signals.pet_appearance_changed.emit()
        app.check_acheivement()

    def _show_toast(self, text: str, color: str):
        self.toast_label.setText(text)
        self.toast_label.setStyleSheet(
            f"color: {color}; font-size: 12px; min-height: 20px;"
        )

    def _confirm_purchase(self, pet_name: str, cost: int) -> bool:
        dialog = PurchaseConfirmDialog(pet_name, cost, self.mgr.get_coins(), self)
        return dialog.exec() == QDialog.DialogCode.Accepted
