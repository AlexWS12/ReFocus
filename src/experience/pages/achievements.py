from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QGridLayout
from PySide6.QtCore import Qt
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
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setObjectName("achievementsContainer")
        self.container_layout = QGridLayout()
        self.container_layout.setSpacing(16)
        self.container_layout.setContentsMargins(24, 16, 24, 16)
        for column in range(3):
            self.container_layout.setColumnStretch(column, 1)
        container.setLayout(self.container_layout)
        scroll.setWidget(container)

        self.page_layout.addWidget(scroll)

        # Load achievements
        self.achievement_manager = Achievement_Manager()
        self.progress = self.achievement_manager.get_progress()

        self._refresh_state()

    def create_card(self):
        columns = 3
        for index, (achievement, info) in enumerate(ACHIEVMENT_CATALOG.items()):
            description = info["description"]
            goal = info["goal"]
            icon = info["icon"]

            if self.progress[achievement] >= goal:
                completed = True
            else:
                completed = False

            row = index // columns
            column = index % columns
            self.container_layout.addWidget(
                Achievement_Card(achievement, description, self.progress[achievement], goal, completed, icon),
                row,
                column,
            )

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _refresh_state(self):
        self.progress = self.achievement_manager.get_progress()
        self._clear_layout(self.container_layout)
        self.create_card()

        
    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_state()
    
