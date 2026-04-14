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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        app = QApplication.instance()
        self.data = app.database_reader.get_topbar_data()

        # set up the main window
        self.setWindowTitle("Study Tracker Partner")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

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
        self.pages_stack.setMaximumWidth(800)
        self.pages_stack.setMaximumHeight(600)

        # add pages to stack
        self.pages_stack.addWidget(Dashboard(self))
        self.pages_stack.addWidget(Session(self))
        self.pages_stack.addWidget(Report(self))
        self.pages_stack.addWidget(VirtualPet(self))
        self.pages_stack.addWidget(Achievements(self))
        self.pages_stack.addWidget(Settings(self))
        self.pages_stack.addWidget(Setup(self))
        self.pages_stack.setCurrentIndex(0)

        # center pages both horizontally and vertically
        pages_row = QHBoxLayout()
        pages_row.setContentsMargins(0, 0, 0, 0)
        pages_row.addStretch(1)
        pages_row.addWidget(self.pages_stack)
        pages_row.addStretch(1)

        pages_wrapper = QVBoxLayout()
        pages_wrapper.setContentsMargins(0, 0, 0, 0)
        pages_wrapper.addStretch(1)
        pages_wrapper.addLayout(pages_row)
        pages_wrapper.addStretch(1)
        self.topbar_pages_layout.addLayout(pages_wrapper)

        self.show()

    def showEvent(self, event):
        super().showEvent(event)
        app = QApplication.instance()
        self.data = app.database_reader.get_topbar_data()
        self.topbar.refresh(self.data)