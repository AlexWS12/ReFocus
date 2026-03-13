from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

class TopBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        # Set up layout for widget
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        # Initilize widget labels
        self.level = QLabel(f"Level {parent.data['level']}")
        self.exp = QLabel(f"{parent.data['exp']} xp")
        self.coin = QLabel(f"{parent.data['coins']} coins")

        # Add Widget to layout
        self.layout.addWidget(self.level)
        self.layout.addWidget(self.exp)
        self.layout.addWidget(self.coin)
        