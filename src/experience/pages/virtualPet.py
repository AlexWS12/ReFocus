from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QApplication,
    QDialog, QPushButton,
)
from PySide6.QtCore import Qt

from src.experience.widgets.centered_label import CenteredLabel
from src.experience.widgets.pet_view import PetView
from src.experience.widgets.pet_card import PetCard
from src.experience.pet_catalog import PET_CATALOG
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
            card = PetCard(pet_id, info["name"], info["sprite"], self)
            card.clicked.connect(self._on_card_clicked)
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

        pet_info = PET_CATALOG.get(active, {})
        self.pet_name_label.setText(pet_info.get("name", ""))
        self.coins_label.setText(f"{coins} coins")

        for pet_id, card in self._cards.items():
            info = PET_CATALOG[pet_id]
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

        if pet_id == active:
            self._show_toast("Already equipped!", "#8892a4")
            return

        if self.mgr.owns_pet(pet_id):
            self.mgr.set_active_pet(pet_id)
            self._emit_change()
            self._show_toast(f"Switched to {PET_CATALOG[pet_id]['name']}!", "#3b7deb")
            return

        cost = PET_CATALOG[pet_id]["cost"]
        if self.mgr.get_coins() < cost:
            self._show_toast("Not enough coins!", "#e74c3c")
            return

        pet_name = PET_CATALOG[pet_id]["name"]
        if not self._confirm_purchase(pet_name, cost):
            self._show_toast("Purchase cancelled.", "#8892a4")
            return

        if not self.mgr.purchase_pet(pet_id):
            self._show_toast("Purchase failed. Please try again.", "#e74c3c")
            return

        self.mgr.set_active_pet(pet_id)
        self._emit_change()
        self._show_toast(
            f"Purchased and equipped {PET_CATALOG[pet_id]['name']}!", "#27ae60",
        )

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

    def _confirm_purchase(self, pet_name: str, cost: int) -> bool:
        dialog = PurchaseConfirmDialog(pet_name, cost, self.mgr.get_coins(), self)
        return dialog.exec() == QDialog.DialogCode.Accepted
