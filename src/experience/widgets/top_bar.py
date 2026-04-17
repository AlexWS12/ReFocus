from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QProgressBar

from src.experience.widgets.centered_label import CenteredLabel
from src.core.database_reader import DatabaseReader


class TopBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.db = DatabaseReader()
        current_xp, xp_needed = self.db.get_xp_progress()

        # Set up layout for widget
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        # Initialize widget labels
        self.level = CenteredLabel(f"Level {parent.data['level']}")
        self.level.setObjectName("levelLabel")

        self.xp_bar = QProgressBar()
        self.xp_bar.setObjectName("xpBar")
        self.xp_bar.setMinimum(0)
        self.xp_bar.setMaximum(int(xp_needed))
        self.xp_bar.setValue(int(current_xp))
        self.xp_bar.setTextVisible(False)
        self.xp_bar.setFixedWidth(300)

        self.xp_label = CenteredLabel(f"{int(current_xp)} / {int(xp_needed)} xp")
        self.xp_label.setObjectName("xpLabel")

        self.coin = CenteredLabel(f"{parent.data['coins']} coins")
        self.coin.setObjectName("coinLabel")

        # Add Widget to layout
        self.layout.addWidget(self.level)
        self.layout.addWidget(self.xp_bar)
        self.layout.addWidget(self.xp_label)
        self.layout.addWidget(self.coin)

    def refresh(self, data):
        current_xp, xp_needed = self.db.get_xp_progress()
        self.level.setText(f"Level {data['level']}")
        self.xp_bar.setMaximum(int(xp_needed))
        self.xp_bar.setValue(int(current_xp))
        self.coin.setText(f"{data['coins']} coins")
        self.xp_label.setText(f"{int(current_xp)} / {int(xp_needed)} xp")