from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication as QtApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

class VisionStream(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.app = QtApplication.instance()
        self.vision_manager = self.app.vision_manager
        self.image_label = QLabel("Camera is idle")
        self.image_label.setObjectName("secondaryLabel")
        self.image_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label)

        self.vision_manager.frame_ready.connect(self.update_frame)

    def update_frame(self, annotated):
        h, w, ch = annotated.shape
        bytes_per_line = ch * w
        qimg = QImage(annotated.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        pix = QPixmap.fromImage(qimg).scaled(
            self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.image_label.setPixmap(pix)

    def start_stream(self):
        self.vision_manager.start()

    def stop_stream(self):
        self.vision_manager.stop()
        self.image_label.setText("Camera is idle")

    def closeEvent(self, event):
        self.vision_manager.frame_ready.disconnect(self.update_frame)
        self.stop_stream()
        super().closeEvent(event)


