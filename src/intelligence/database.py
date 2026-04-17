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
            self.conn.row_factory = sqlite3.Row # Converts query results from tuples to dictionary objects
            self.conn.execute("PRAGMA foreign_keys = ON")  # SQLite disables FK enforcement by default
        return self.conn


    def _init_db(self):
        self._get_connection()  # Ensure connection is established
        self._create_sessions_table()
        self._create_user_stats_table()
        self._create_events_table()
        self._create_achievements_table()
        self._create_user_settings_table() # New table for user settings to control distraction type toggles
        self._migrate_inventory_table()
        self._create_inventory_table()
        self._migrate_sessions_table()
        self._migrate_current_pet_default()
        self._migrate_equipped_accessories()
        self.conn.commit()


    def _create_sessions_table(self):
        cursor = self._get_connection().cursor()

        # Create a SESSIONS table to store user session data
        # id                      - unique identifier for each session
        # start_time              - time the session started (ISO 8601) --- we will discuss further into this next week
        # end_time                - time the session ended (ISO 8601); NULL while active  --- we will discuss further into this next week
        # duration                - total duration of the session in seconds
        # focused_time            - time spent focused (not distracted) in seconds
        # events                  - total number of distraction events
        # time_away               - total time spent away from the desk in seconds
        # look_away_time          - total time spent looking away from the screen in seconds
        # phone_time              - total time spent on phone distractions in seconds
        # distraction_time        - total time spent distracted in seconds
        # phone_distractions      - distractions caused by phone use
        # look_away_distractions  - distractions caused by looking away from the screen
        # left_desk_distractions  - distractions caused by leaving the desk
        # app_distractions        - distractions caused by switching to off-task apps
        # idle_distractions       - distractions caused by inactivity
        # focus_percentage        - focused_time / duration as a percentage
        # score                   - session performance score
        # points_earned           - experience points earned this session
        # coins_earned            - coins earned this session

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration INTEGER DEFAULT 0,
                focused_time INTEGER DEFAULT 0,
                events INTEGER DEFAULT 0,
                time_away INTEGER DEFAULT 0,
                look_away_time INTEGER DEFAULT 0,
                phone_time INTEGER DEFAULT 0,
                distraction_time INTEGER DEFAULT 0,
                phone_distractions INTEGER DEFAULT 0,
                look_away_distractions INTEGER DEFAULT 0,
                left_desk_distractions INTEGER DEFAULT 0,
                app_distractions INTEGER DEFAULT 0,
                idle_distractions INTEGER DEFAULT 0,
                focus_percentage REAL DEFAULT 0,
                score INTEGER DEFAULT 0,
                points_earned INTEGER DEFAULT 0,
                coins_earned INTEGER DEFAULT 0
            )
        ''')

        # Lightweight schema migration for existing local databases created before
        # the phone-time breakdown existed.
        existing_columns = {
            row["name"] for row in cursor.execute("PRAGMA table_info(sessions)").fetchall()
        }
        if "phone_time" not in existing_columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN phone_time INTEGER DEFAULT 0")


    def _create_user_stats_table(self):
        cursor = self._get_connection().cursor()

        # Create a USER_STATS table to store overall user statistics
        # id                 - enforced singleton row (always 1)
        # level              - current user level
        # avg_focus_time     - average focus time per session in seconds
        # total_sessions     - total number of completed sessions
        # total_time_spent   - cumulative time spent in sessions in seconds
        # coins              - total coins earned by the user
        # exp                - total experience points earned by the user
        # total_distractions - total distractions across all sessions
        # total_look_aways   - total look-aways across all sessions
        # current_pet        - the pet the user currently has equipped
        # created_at         - time the user stats row was created (ISO 8601)
        # updated_at         - time the user stats row was last updated (ISO 8601)

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                level INTEGER DEFAULT 1,
                avg_focus_time REAL DEFAULT 0.0,
                total_sessions INTEGER DEFAULT 0,
                total_time_spent INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 0,
                exp INTEGER DEFAULT 0,
                total_distractions INTEGER DEFAULT 0,
                total_look_aways INTEGER DEFAULT 0,
                current_pet TEXT DEFAULT 'cat',
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        # Seed the singleton row so reads always find a record
        cursor.execute("INSERT OR IGNORE INTO user_stats (id) VALUES (1)")


    def _create_events_table(self):
        cursor = self._get_connection().cursor()

        # Create an EVENTS table to record individual events during sessions
        # id         - unique identifier for each event
        # session_id - the session during which the event occurred
        # event_type - the type of event (e.g. distraction, look_away)
        # timestamp  - time the event occurred (ISO 8601)
        # duration   - duration of the event in seconds
        # details    - optional extra info about the event

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                duration INTEGER DEFAULT 0,
                details TEXT,
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
        # emoji       - emoji icon representing the achievement
        # unlocked    - 1 if earned, 0 otherwise
        # unlocked_at - time the achievement was earned (ISO 8601); NULL until earned
        # progress    - current progress toward the achievement target
        # target      - value needed to unlock the achievement

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                criteria TEXT NOT NULL,
                emoji TEXT DEFAULT '🏆',
                unlocked INTEGER DEFAULT 0,
                unlocked_at TEXT,
                progress INTEGER DEFAULT 0,
                target INTEGER DEFAULT 1
            )
        ''')

    def _create_user_settings_table(self):
        cursor = self._get_connection().cursor()

        # Create a USER_SETTINGS table to store per-distraction-type toggles.
        # Follows the same singleton pattern as user_stats (id forced to 1).
        #
        # Each boolean column controls whether the corresponding distraction type
        # is tracked during study sessions:
        #   1 (default) = enabled  — the distraction will be detected, logged, and
        #                             penalized in score calculation.
        #   0           = disabled — the Camera still runs its detectors, but
        #                             SessionManager.log_distraction() silently
        #                             discards events of this type.
        #
        # All default to 1 so existing behavior is preserved until the user
        # explicitly disables a type from the settings UI.
        #
        # id                           - enforced singleton row (always 1)
        # phone_detection_enabled      - toggle for phone-use distractions
        # look_away_detection_enabled  - toggle for look-away distractions
        # left_desk_detection_enabled  - toggle for left-desk distractions
        # app_detection_enabled        - toggle for app-switch distractions
        # idle_detection_enabled       - toggle for idle/inactivity distractions
        # updated_at                   - ISO 8601 timestamp of last settings change

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                phone_detection_enabled INTEGER DEFAULT 1,
                look_away_detection_enabled INTEGER DEFAULT 1,
                left_desk_detection_enabled INTEGER DEFAULT 1,
                app_detection_enabled INTEGER DEFAULT 1,
                idle_detection_enabled INTEGER DEFAULT 1,
                updated_at TEXT
            )
        ''')
        # Seed the singleton row so reads always find a record (same as user_stats)
        cursor.execute("INSERT OR IGNORE INTO user_settings (id) VALUES (1)")

    def _create_inventory_table(self):
        cursor = self._get_connection().cursor()

        # Tracks which pets (and later accessories) the user owns.
        # item_type  - 'pet' or 'accessory'
        # item_id    - key from PET_CATALOG / ACCESSORY_CATALOG
        # name       - custom name for the pet
        # acquired_at - ISO 8601 timestamp of purchase
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                name TEXT,
                acquired_at TEXT,
                UNIQUE(item_type, item_id)
            )
        ''')
        cursor.execute(
            "INSERT OR IGNORE INTO inventory (item_type, item_id, name) VALUES ('pet', 'cat', 'Calico Cat')"
        )
        # Set default names for existing pets without names
        cursor.execute("""
            UPDATE inventory SET name = CASE item_id
                WHEN 'cat' THEN 'Calico Cat'
                WHEN 'dog' THEN 'Pup'
                WHEN 'frog' THEN 'Frog'
                ELSE item_id
            END WHERE name IS NULL AND item_type = 'pet'
        """)

    def _migrate_inventory_table(self):
        # Migration: add the name column to the existing inventory table.
        # This allows existing databases to support pet naming without losing data.
        cursor = self._get_connection().cursor()
        try:
            cursor.execute('''
                ALTER TABLE inventory ADD COLUMN name TEXT
            ''')
        except Exception:
            pass  # Column already exists from a previous migration run

    def _migrate_current_pet_default(self):
        cursor = self._get_connection().cursor()
        cursor.execute(
            "UPDATE user_stats SET current_pet = 'cat' WHERE id = 1 AND current_pet IN ('default', 'panther')"
        )

    def _migrate_sessions_table(self):
        # Schema migration: add the enabled_distractions column to the existing
        # sessions table.  This column stores a JSON array of the distraction type
        # string values that were enabled when the session was recorded, e.g.:
        #   '["app_distraction", "left_desk_distraction", "phone_distraction"]'
        #
        # Why this column is needed:
        #   When a user disables a distraction type and then records a session,
        #   the disabled type's count will naturally be 0.  Without this column,
        #   PatternAnalyzer cannot tell whether a 0 means "the user was perfectly
        #   focused" or "detection was turned off."  The snapshot resolves that
        #   ambiguity so ML features can exclude disabled types from training data.
        #
        # Legacy sessions (recorded before this migration) will have NULL in this
        # column, which is interpreted as "all five types were enabled."
        #
        # ALTER TABLE is wrapped in try/except because SQLite does not support
        # IF NOT EXISTS for columns — if the migration has already run, the
        # duplicate ALTER will raise an OperationalError, which we silently ignore.
        cursor = self._get_connection().cursor()
        try:
            cursor.execute('''
                ALTER TABLE sessions ADD COLUMN enabled_distractions TEXT
            ''')
        except Exception:
            pass  # Column already exists from a previous migration run

    def _migrate_equipped_accessories(self):
        # Schema migration: add the `equipped_accessories` column to user_stats.
        #
        # Stored as a JSON array of accessory ids that match keys in
        # ACCESSORY_CATALOG, e.g. '["top_hat"]'.  Only one accessory per slot
        # is allowed; PetManager enforces that invariant on writes.
        #
        # NULL / empty string is interpreted as "no accessories equipped"
        # which keeps legacy databases (created before this migration) working
        # without any extra handling.
        cursor = self._get_connection().cursor()
        try:
            cursor.execute(
                "ALTER TABLE user_stats ADD COLUMN equipped_accessories TEXT DEFAULT '[]'"
            )
        except Exception:
            pass  # Column already exists from a previous migration run

    # Close the database connection when done
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None


# Singleton accessor: returns a shared SQLite connection so all callers
# (SessionManager, etc.) operate on the same DB without opening multiple handles.
_db_instance = None

def get_database():
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance._get_connection()
