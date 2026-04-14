from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

class Achievement_Card(QFrame):
    def __init__(self, name: str, description: str, progress: int, goal: int, unlocked: bool, icon_path: str):
        super().__init__()
        self.setObjectName("achievementCard")

        # Vertical tile layout
        card_layout = QVBoxLayout()
        self.setLayout(card_layout)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.icon = QLabel()
        pixmap = QPixmap(icon_path).scaled(140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.icon.setPixmap(pixmap)
        self.icon.setAlignment(Qt.AlignCenter)

        progress = min(progress, goal)
        title = QLabel(name)
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        description_label = QLabel(description)
        description_label.setAlignment(Qt.AlignCenter)
        description_label.setWordWrap(True)
        progress_label = QLabel(f"{progress} / {goal}")
        progress_label.setAlignment(Qt.AlignCenter)

        card_layout.addWidget(self.icon)
        card_layout.addWidget(title)
        card_layout.addWidget(description_label)
        card_layout.addStretch()
        card_layout.addWidget(progress_label)

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