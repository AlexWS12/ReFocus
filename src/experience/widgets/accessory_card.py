from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QCursor


class AccessoryCard(QFrame):
    """Clickable card showing an accessory thumbnail, name, and status.

    States (mirrors PetCard):
        * equipped   - currently worn; click to unequip
        * owned      - owned but not worn; click to equip
        * buyable    - not owned, user can afford; Buy button visible
        * locked     - not owned, user can't afford; Buy button disabled

    Emits:
        clicked(str)          - card body click, payload = accessory_id
        purchaseClicked(str)  - Buy button click, payload = accessory_id
    """

    clicked = Signal(str)
    purchaseClicked = Signal(str)

    def __init__(
        self,
        accessory_id: str,
        name: str,
        sprite_path: str,
        parent=None,
    ):
        super().__init__(parent)
        self.accessory_id = accessory_id
        self.setObjectName("petCard")  # Reuse the pet card QSS styling
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(120, 170)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(6)
        self.setLayout(layout)

        self.thumb = QLabel()
        self.thumb.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(sprite_path)
        scaled = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.thumb.setPixmap(scaled)
        layout.addWidget(self.thumb)

        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("font-weight: 600; font-size: 12px;")
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("petCardStatus")
        layout.addWidget(self.status_label)

        self.purchase_button = QPushButton("Buy")
        self.purchase_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.purchase_button.setFixedHeight(26)
        self.purchase_button.setStyleSheet(
            "background-color: #3b7deb; color: #fff; border: none; "
            "border-radius: 6px; font-size: 11px; padding: 2px 8px;"
        )
        self.purchase_button.clicked.connect(self._on_purchase_clicked)
        layout.addWidget(self.purchase_button)

    def set_state(
        self,
        *,
        equipped: bool = False,
        owned: bool = False,
        cost: int = 0,
        affordable: bool = True,
    ):
        if equipped:
            self.status_label.setText("Equipped")
            self.status_label.setStyleSheet(
                "color: #3b7deb; font-weight: 600; font-size: 11px;"
            )
            self.setProperty("cardState", "equipped")
            self.purchase_button.hide()
        elif owned:
            self.status_label.setText("Owned")
            self.status_label.setStyleSheet(
                "color: #8892a4; font-size: 11px;"
            )
            self.setProperty("cardState", "owned")
            self.purchase_button.hide()
        else:
            self.status_label.setText(f"{cost} coins")
            self.purchase_button.show()
            if affordable:
                self.status_label.setStyleSheet(
                    "color: #f5a623; font-weight: 600; font-size: 11px;"
                )
                self.setProperty("cardState", "buyable")
                self.purchase_button.setEnabled(True)
            else:
                self.status_label.setStyleSheet(
                    "color: #e74c3c; font-size: 11px;"
                )
                self.setProperty("cardState", "locked")
                self.purchase_button.setEnabled(False)

        self.style().unpolish(self)
        self.style().polish(self)

    def _on_purchase_clicked(self):
        self.purchaseClicked.emit(self.accessory_id)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.accessory_id)
        super().mousePressEvent(event)
