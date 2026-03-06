import sqlite3


class Database:
    def __init__(self, db_path: str = "data.db"):
        self.db_path = db_path
        self.conn = None
        self._init_db()


    # Protected method get_connection with return type sqlite3.Connection
    def _get_connection(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            # Converts query results from tuples to dictionary objects
            self.conn.row_factory = sqlite3.Row
        return self.conn


    def _init_db(self):
        self._get_connection()  # Ensure connection is established
        self._create_sessions_table()
        self._create_user_stats_table()
        self._create_events_table()
        self._create_achievements_table()
        self.conn.commit()


    def _create_sessions_table(self):
        cursor = self._get_connection().cursor()

        # Create a SESSIONS table to store user session data
        # id            - unique identifier for each session
        # start_time    - time the session started (ISO 8601)
        # end_time      - time the session ended (ISO 8601); NULL while active
        # duration      - total duration of the session in seconds
        # events        - total number of events (distractions / look-aways) during the session
        # time_away     - total time spent away from the desk in seconds
        # look_away_time    - total time spent looking away from the screen in seconds
        # distraction_time  - total time spent distracted in seconds

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration INTEGER DEFAULT 0,
                events INTEGER DEFAULT 0,
                time_away INTEGER DEFAULT 0,
                look_away_time INTEGER DEFAULT 0,
                distraction_time INTEGER DEFAULT 0
            )
        ''')


    def _create_user_stats_table(self):
        cursor = self._get_connection().cursor()

        # Create a USER_STATS table to store overall user statistics
        # id                - enforced singleton row (always 1)
        # avg_focus_time    - average focus time per session in seconds
        # total_sessions    - total number of completed sessions
        # total_time_spent  - cumulative time spent in sessions in seconds
        # coins             - total coins earned by the user
        # exp               - total experience points earned by the user
        # total_distractions - total distractions across all sessions
        # total_look_aways  - total look-aways across all sessions

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                avg_focus_time REAL DEFAULT 0.0,
                total_sessions INTEGER DEFAULT 0,
                total_time_spent INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 0,
                exp INTEGER DEFAULT 0,
                total_distractions INTEGER DEFAULT 0,
                total_look_aways INTEGER DEFAULT 0
            )
        ''')


    def _create_events_table(self):
        cursor = self._get_connection().cursor()

        # Create an EVENTS table to record individual events during sessions
        # id         - unique identifier for each event
        # session_id - the session during which the event occurred
        # event_type - the type of event (e.g. distraction, look_away)
        # timestamp  - time the event occurred (ISO 8601)
        # duration   - duration of the event in seconds

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                duration INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        ''')


    def _create_achievements_table(self):
        cursor = self._get_connection().cursor()

        # Create an ACHIEVEMENTS table to store user achievements
        # id          - unique identifier for each achievement
        # name        - name of the achievement
        # description - description of the achievement
        # criteria    - criteria for earning the achievement (e.g. "Focus for 1 hour straight")
        # unlocked    - 1 if earned, 0 otherwise
        # unlocked_at - time the achievement was earned (ISO 8601); NULL until earned

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                criteria TEXT NOT NULL,
                unlocked INTEGER DEFAULT 0,
                unlocked_at TEXT
            )
        ''')


    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
