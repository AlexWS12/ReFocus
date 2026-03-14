from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class total_exp(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(QLabel("Total Exp:"))
        self.layout.addWidget(QLabel(f"{parent.data['total_exp']}"))