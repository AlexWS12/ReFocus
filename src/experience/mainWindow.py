from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QVBoxLayout
from src.core.database_reader import DatabaseReader
from src.experience.sideBar import Sidebar
from src.experience.pages.dashboard import dashboard
from src.experience.pages.session import session
from src.experience.pages.report import report
from src.experience.pages.virtualPet import virtualPet
from src.experience.pages.achievements import achievements

from src.experience.widgets.topBar import TopBar

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.database_reader = DatabaseReader()
        self.data = self.database_reader.get_topbar_data()

        # set up the main window
        self.setWindowTitle("Study Tracker Partner")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        # main container for the main window
        self.main_container = QWidget()
        self.layout = QHBoxLayout()
        self.main_container.setLayout(self.layout)
        self.setCentralWidget(self.main_container)

        self.topbar_pages_container = QWidget()
        self.topbar_pages_layout = QVBoxLayout()
        self.topbar_pages_container.setLayout(self.topbar_pages_layout)

        # add sidebar and top bar pages container to layout
        self.sidebar = Sidebar(self)
        self.layout.addWidget(self.sidebar)
        self.layout.addWidget(self.topbar_pages_container)

        self.topbar = TopBar(self)
        self.topbar_pages_layout.addWidget(self.topbar)

        # intialize stacked pages
        self.pages_stack = QStackedWidget()

        # add pages to stack
        self.pages_stack.addWidget(dashboard(self))
        self.pages_stack.addWidget(session(self))
        self.pages_stack.addWidget(report(self))
        self.pages_stack.addWidget(virtualPet(self))
        self.pages_stack.addWidget(achievements(self))
        self.pages_stack.setCurrentIndex(0)
        
        self.topbar_pages_layout.addWidget(self.pages_stack)

        self.show()