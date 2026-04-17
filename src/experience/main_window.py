from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QVBoxLayout
from src.core.qApplication import QApplication
from src.experience.side_bar import Sidebar
from src.experience.pages.dashboard import Dashboard
from src.experience.pages.session import Session
from src.experience.pages.report import Report
from src.experience.pages.virtualPet import VirtualPet
from src.experience.pages.achievements import Achievements
from src.experience.pages.settings import Settings
from src.experience.pages.setup import Setup
from src.experience.widgets.top_bar import TopBar
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel
from src.experience.widgets.achievement_catalog import ACHIEVMENT_CATALOG
from PySide6.QtGui import QPixmap

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        app = QApplication.instance()
        self.data = app.database_reader.get_topbar_data()

        # set up the main window
        self.setWindowTitle("ReFocus")
        self.setMinimumWidth(860)
        self.setMinimumHeight(800)

        # main container for the main window
        self.main_container = QWidget()
        self.main_container.setObjectName("mainContainer")
        self.main_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.main_container.setLayout(self.layout)
        self.setCentralWidget(self.main_container)

        # container for the top bar and pages
        self.topbar_pages_container = QWidget()
        self.topbar_pages_container.setObjectName("mainContent")
        self.topbar_pages_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.topbar_pages_layout = QVBoxLayout()
        self.topbar_pages_layout.setContentsMargins(0, 0, 0, 0)
        self.topbar_pages_layout.setSpacing(0)
        self.topbar_pages_container.setLayout(self.topbar_pages_layout)

        # add sidebar and top bar pages container to main layout
        self.sidebar = Sidebar(self)
        self.sidebar.setFixedWidth(140)
        self.layout.addWidget(self.sidebar)
        self.layout.addWidget(self.topbar_pages_container)

        self.topbar = TopBar(self)
        self.topbar_pages_layout.addWidget(self.topbar)

        # intialize stacked pages
        self.pages_stack = QStackedWidget()
        self.pages_stack.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # add pages to stack
        self.pages_stack.addWidget(Dashboard(self))
        self.pages_stack.addWidget(Session(self))
        self.pages_stack.addWidget(Report(self))
        self.pages_stack.addWidget(VirtualPet(self))
        self.pages_stack.addWidget(Achievements(self))
        self.pages_stack.addWidget(Settings(self))
        self.pages_stack.addWidget(Setup(self))
        self.pages_stack.setCurrentIndex(0)

        self.topbar_pages_layout.addWidget(self.pages_stack, stretch=1)

                # Achievement toast
        self.achievement_container = QWidget()
        self.achievement_container.setObjectName("achievementPopup")
        achievement_layout = QHBoxLayout(self.achievement_container)
        achievement_layout.setContentsMargins(10, 6, 10, 6)
        achievement_layout.setSpacing(8)

        self.achievement_icon = QLabel()
        self.achievement_icon.setFixedSize(50, 50)
        achievement_layout.addWidget(self.achievement_icon)

        self.achievement_text = QLabel("")
        self.achievement_text.setObjectName("achievementText")
        achievement_layout.addWidget(self.achievement_text)

        self.achievement_container.hide()
        self.topbar_pages_layout.insertWidget(1, self.achievement_container)

        app.signals.achievement_unlocked.connect(self._show_achievement_popup)

        self.show()
       
    def showEvent(self, event):
        super().showEvent(event)
        app = QApplication.instance()
        self.data = app.database_reader.get_topbar_data()
        self.topbar.refresh(self.data)

    def _show_achievement_popup(self, achievement_name: str):
        info = ACHIEVMENT_CATALOG.get(achievement_name, {})
        icon_path = info.get("icon", "")
        pixmap = QPixmap(icon_path).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.achievement_icon.setPixmap(pixmap)
        self.achievement_text.setText(f"Achievement Unlocked: {achievement_name}!")
        self.achievement_container.show()
        QTimer.singleShot(4000, self.achievement_container.hide)