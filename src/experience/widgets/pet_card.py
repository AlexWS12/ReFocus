from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QCursor


class PetCard(QFrame):
    # Clickable card showing a pet thumbnail, name, and purchase/equip status

    clicked = Signal(str)
    purchaseClicked = Signal(str)

    def __init__(self, pet_id: str, name: str, sprite_path: str, parent=None):
        super().__init__(parent)
        self.pet_id = pet_id
        self.setObjectName("petCard")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(140, 190)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(6)
        self.setLayout(layout)

        self.thumb = QLabel()
        self.thumb.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(sprite_path)
        scaled = pixmap.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.thumb.setPixmap(scaled)
        layout.addWidget(self.thumb)

        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(self.name_label)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("petCardStatus")
        layout.addWidget(self.status_label)

        self.purchase_button = QPushButton("Buy")
        self.purchase_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.purchase_button.setFixedHeight(30)
        self.purchase_button.setStyleSheet(
            "background-color: #3b7deb; color: #fff; border: none; border-radius: 6px; font-size: 12px; padding: 2px 10px;"
        )
        self.purchase_button.clicked.connect(self._on_purchase_clicked)
        layout.addWidget(self.purchase_button)

    def set_state(self, *, equipped: bool = False, owned: bool = False, cost: int = 0, affordable: bool = True):
        if equipped:
            self.status_label.setText("Equipped")
            self.status_label.setStyleSheet("color: #3b7deb; font-weight: 600; font-size: 12px;")
            self.setProperty("cardState", "equipped")
            self.purchase_button.hide()
        elif owned:
            self.status_label.setText("Owned")
            self.status_label.setStyleSheet("color: #8892a4; font-size: 12px;")
            self.setProperty("cardState", "owned")
            self.purchase_button.hide()
        else:
            self.status_label.setText(f"{cost} coins")
            self.purchase_button.show()
            if affordable:
                self.status_label.setStyleSheet("color: #f5a623; font-weight: 600; font-size: 12px;")
                self.setProperty("cardState", "buyable")
                self.purchase_button.setEnabled(True)
            else:
                self.status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
                self.setProperty("cardState", "locked")
                self.purchase_button.setEnabled(False)

        self.style().unpolish(self)
        self.style().polish(self)

    def _on_purchase_clicked(self):
        self.purchaseClicked.emit(self.pet_id)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.pet_id)
        super().mousePressEvent(event)
