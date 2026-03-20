from PySide6.QtWidgets import QWidget, QHBoxLayout

from src.experience.widgets.centered_label import CenteredLabel


class TopBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        # Set up layout for widget
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        # Initialize widget labels
        self.level = CenteredLabel(f"Level {parent.data['level']}")
        self.exp = CenteredLabel(f"{parent.data['exp']} xp")
        self.coin = CenteredLabel(f"{parent.data['coins']} coins")
        self.exp.setObjectName("xpLabel")
        self.coin.setObjectName("coinLabel")

        # Add Widget to layout
        self.layout.addWidget(self.level)
        self.layout.addWidget(self.exp)
        self.layout.addWidget(self.coin)
        