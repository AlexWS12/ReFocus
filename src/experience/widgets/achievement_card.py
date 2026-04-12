from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

class Achievement_Card(QFrame):
    def __init__(self, name: str, description: str, progress: int, goal: int, unlocked: bool, icon_path: str):
        super().__init__()
        self.setObjectName("achievementCard")

        # Set up layout
        card_layout = QHBoxLayout()
        self.setLayout(card_layout)
        card_layout.setContentsMargins(12, 8, 12, 8)
        card_layout.setSpacing(4)
        self.setMinimumHeight(50)

        left = QVBoxLayout()
        left.addWidget(QLabel(name))
        left.addWidget(QLabel(description))

        self.icon = QLabel()
        pixmap = QPixmap(icon_path)
        pixmap = QPixmap(icon_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.icon.setPixmap(pixmap)

        card_layout.addWidget(self.icon)
        card_layout.addLayout(left)
        card_layout.addStretch()
        progress = min(progress, goal)
        card_layout.addWidget(QLabel(f"{progress} / {goal}"))

        # Turns background green if goal is meet
        if unlocked:
            self.setStyleSheet("""
                QFrame { background-color: #2ecc71; border-radius: 8px; }
                QFrame QLabel { color: white; background: transparent; }
            """)
        else:
            self.setStyleSheet("""
                QFrame { background-color: #2c2c2c; border-radius: 8px; }
                QFrame QLabel { color: white; background: transparent; }
            """)