from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

class TopBar(QWidget):
    def __init__(self):
        super().__init__()

        # Set up layout for widget
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        # Initilize widget labels
        self.level = QLabel("Level 100")
        self.exp = QLabel("1000xp")
        self.coin = QLabel("10000")

        # Add Widget to layout
        self.layout.addWidget(self.level)
        self.layout.addWidget(self.exp)
        self.layout.addWidget(self.coin)
        