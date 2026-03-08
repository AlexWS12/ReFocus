from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap, Qt

class petWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Virtual Pet")

        # Load the pet image from the static assets folder
        self.image = QPixmap("src/experience/static/Panther.png")

         # Display the image inside a label
        self.label = QLabel()

        scaled = self.image.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(scaled)
        self.setFixedSize(100, 100)

         # Container to hold the label
        self.container = QWidget()
        self.layout = QVBoxLayout()
        self.container.setLayout(self.layout)
        self.layout.addWidget(self.label) 
        self.setCentralWidget(self.container)

        

