from src.intelligence.database import Database
from src.core.qApplication import QApplication

def main():
    db = Database()
    q_application = QApplication()
    q_application.run()

if __name__ == "__main__":
    main()
