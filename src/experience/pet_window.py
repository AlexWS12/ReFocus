from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QEvent

from src.experience.widgets.centered_label import CenteredLabel

class petWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Virtual Pet")

        # Set the window flags to make it frameless and stay on top
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Set the background to transparent
        self.setStyleSheet("background: transparent;")

        # Load the pet image from the static assets folder
        self.image = QPixmap("src/experience/static/Panther.png")

        # Display the image inside a label
        self.label = CenteredLabel("")

        # Scale the image to 80x80 pixels while maintaining aspect ratio
        scaled = self.image.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(scaled)
        self.setFixedSize(100, 100)

        # Container to hold the label
        self.container = QWidget()
        self.layout = QVBoxLayout()
        self.container.setLayout(self.layout)
        self.layout.addWidget(self.label)
        self.setCentralWidget(self.container)

        # Draggable window
        self.drag_position = None
        self.label.installEventFilter(self)
        self.label.setCursor(Qt.OpenHandCursor)

    # Event filter for the pet window to make it draggable
    def eventFilter(self, obj, event):
        if obj == self.label:
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.drag_position = event.globalPosition().toPoint()
                    self.label.setCursor(Qt.ClosedHandCursor)
                    return True
            elif event.type() == QEvent.MouseMove:
                if event.buttons() & Qt.LeftButton and self.drag_position is not None:
                    delta = event.globalPosition().toPoint() - self.drag_position
                    self.move(self.pos() + delta)
                    self.drag_position = event.globalPosition().toPoint()
                    return True
            elif event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    self.drag_position = None
                    self.label.setCursor(Qt.OpenHandCursor)
                    return True
            elif event.type() == QEvent.MouseButtonDblClick:
                if event.button() == Qt.LeftButton:
                    self._end_session()
                    return True
        return super().eventFilter(obj, event)

    def _end_session(self):
        app = QApplication.instance()
        app.vision_manager.stop_session()
        app.session_manager.end_session()
        app.session_manager.reset()
        app.main_window.pages_stack.setCurrentIndex(0)
        app.main_window.show()
        self.hide()


