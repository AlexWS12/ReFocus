from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from src.experience.widgets.centered_label import CenteredLabel
from src.experience.widgets.achievement_catalog import ACHIEVMENT_CATALOG
from src.experience.widgets.achievement_card import Achievement_Card
from src.experience.achievement_manager import Achievement_Manager

class Achievements(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pageRoot")

        self.page_layout = QVBoxLayout()
        self.page_layout.setContentsMargins(24, 16, 24, 16)
        self.setLayout(self.page_layout)

        self.page_layout.addWidget(CenteredLabel("Achievements"))

        # Scroll function setup
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background-color: #f4f6fb;")
        container_layout = QVBoxLayout()
        container_layout.setSpacing(12)
        container_layout.setContentsMargins(24, 16, 24, 16)
        container.setLayout(container_layout)
        scroll.setWidget(container)

        self.page_layout.addWidget(scroll)

        # Load achievements
        self.achievement_manager = Achievement_Manager()
        self.progress = self.achievement_manager.get_progress()

        for achievement, info in ACHIEVMENT_CATALOG.items():
            description = info["description"]
            goal = info["goal"]
            icon = info["icon"]

            if self.progress[achievement] >= goal:
                completed = True
            else:
                completed = False

            container_layout.addWidget(Achievement_Card(achievement, description, self.progress[achievement], goal, completed, icon))