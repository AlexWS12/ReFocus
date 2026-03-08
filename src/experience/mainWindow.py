from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget
from src.experience.sideBar import Sidebar

from src.experience.pages.dashboard import dashboard
from src.experience.pages.session import session
from src.experience.pages.report import report
from src.experience.pages.virtualPet import virtualPet
from src.experience.pages.achievements import achievements

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # set up the main window
        self.setWindowTitle("Study Tracker Partner")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        # main container for the main window
        self.main_container = QWidget()
        self.layout = QHBoxLayout()
        self.main_container.setLayout(self.layout)
        self.setCentralWidget(self.main_container)

        # intialize stacked pages
        self.pages_stack = QStackedWidget()

        # add pages to stack
        self.pages_stack.addWidget(dashboard(self))
        self.pages_stack.addWidget(session(self))
        self.pages_stack.addWidget(report(self))
        self.pages_stack.addWidget(virtualPet(self))
        self.pages_stack.addWidget(achievements(self))
        self.pages_stack.setCurrentIndex(0)

        # initilize Sidebar
        self.sidebar = Sidebar(self)

        # add sidebar and pages stack to layout
        self.layout.addWidget(self.sidebar)
        self.layout.addWidget(self.pages_stack)

        self.show()