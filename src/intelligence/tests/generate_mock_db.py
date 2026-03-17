"""
Generates mock_data.db — a fake SQLite database for UI development.
Run this script once to (re)create the mock database:
    python generate_mock_db.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "mock_data.db")


def create_tables(conn):
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            duration INTEGER DEFAULT 0,
            focused_time INTEGER DEFAULT 0,
            events INTEGER DEFAULT 0,
            time_away INTEGER DEFAULT 0,
            look_away_time INTEGER DEFAULT 0,
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
        );

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
            current_pet TEXT DEFAULT 'default',
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            duration INTEGER DEFAULT 0,
            details TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        );

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
        );
    ''')


def seed_sessions(conn):
    sessions = [
        # id, start_time, end_time, duration, focused_time, events, time_away,
        # look_away_time, distraction_time, phone, look_away, left_desk, app, idle,
        # focus_pct, score, points, coins
        (1, "2026-03-04T09:00:00", "2026-03-04T10:30:00", 5400, 4212, 6, 180, 300, 908,  1, 2, 1, 1, 1, 78.0, 82, 120, 30),
        (2, "2026-03-05T14:00:00", "2026-03-05T15:00:00", 3600, 3060, 3, 60,  120, 360,  0, 1, 0, 2, 0, 85.0, 91, 95,  20),
        (3, "2026-03-06T08:30:00", "2026-03-06T09:45:00", 4500, 3150, 9, 300, 420, 1050, 3, 3, 1, 2, 0, 70.0, 65, 80,  15),
        (4, "2026-03-07T10:00:00", "2026-03-07T11:30:00", 5400, 5130, 2, 30,  60,  210,  0, 1, 0, 1, 0, 95.0, 98, 150, 40),
        (5, "2026-03-08T13:00:00", "2026-03-08T13:45:00", 2700, 1890, 5, 240, 180, 630,  2, 1, 1, 1, 0, 70.0, 60, 55,  10),
        (6, "2026-03-09T09:15:00", "2026-03-09T11:15:00", 7200, 6480, 4, 120, 300, 420,  1, 2, 0, 1, 0, 90.0, 94, 200, 50),
        (7, "2026-03-10T15:00:00", "2026-03-10T16:00:00", 3600, 2520, 7, 360, 240, 840,  2, 2, 1, 2, 0, 70.0, 63, 70,  12),
    ]
    conn.executemany('''
        INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', sessions)


def seed_user_stats(conn):
    conn.execute('''
        INSERT OR IGNORE INTO user_stats VALUES (
            1, 7, 3774.0, 7, 32400, 177, 770, 36, 12, 'fox',
            '2026-03-04T09:00:00', '2026-03-10T16:00:00'
        )
    ''')


def seed_events(conn):
    events = [
        # session 1
        (1, 1, "phone_distraction",    "2026-03-04T09:22:00", 45,  "Phone screen lit up"),
        (2, 1, "look_away_distraction","2026-03-04T09:45:00", 30,  None),
        (3, 1, "app_distraction",      "2026-03-04T10:01:00", 120, "YouTube opened"),
        (4, 1, "look_away_distraction","2026-03-04T10:10:00", 20,  None),
        (5, 1, "left_desk_distraction","2026-03-04T10:18:00", 180, "Left desk"),
        (6, 1, "idle_distraction",     "2026-03-04T10:25:00", 60,  "No input detected"),
        # session 2
        (7, 2, "look_away_distraction","2026-03-05T14:15:00", 25,  None),
        (8, 2, "app_distraction",      "2026-03-05T14:40:00", 90,  "Discord opened"),
        (9, 2, "app_distraction",      "2026-03-05T14:55:00", 60,  "Discord opened again"),
        # session 4 (best session)
        (10, 4, "look_away_distraction","2026-03-07T10:45:00", 30, None),
        (11, 4, "app_distraction",      "2026-03-07T11:20:00", 60, "Twitter opened"),
        # session 6 (longest session)
        (12, 6, "phone_distraction",    "2026-03-09T09:50:00", 40,  "Phone notification"),
        (13, 6, "look_away_distraction","2026-03-09T10:15:00", 90,  None),
        (14, 6, "look_away_distraction","2026-03-09T10:45:00", 45,  None),
        (15, 6, "app_distraction",      "2026-03-09T11:05:00", 120, "Spotify opened"),
    ]
    conn.executemany('''
        INSERT INTO events VALUES (?,?,?,?,?,?)
    ''', events)


def seed_achievements(conn):
    achievements = [
        # id, name, desc, criteria, emoji, unlocked, unlocked_at, progress, target
        (1,  "First Focus",      "Complete your first study session",           "Complete 1 session",             "🎯", 1, "2026-03-04T10:30:00", 1,  1),
        (2,  "On a Roll",        "Complete 5 sessions",                         "Complete 5 sessions",            "🔥", 1, "2026-03-08T13:45:00", 5,  5),
        (3,  "Dedicated",        "Complete 10 sessions",                        "Complete 10 sessions",           "💪", 0, None,                   7,  10),
        (4,  "Sharp Focus",      "Achieve 90%+ focus in a session",             "Focus percentage >= 90",         "🧠", 1, "2026-03-07T11:30:00", 1,  1),
        (5,  "Phone Away",       "Complete a session with zero phone distractions", "0 phone distractions",      "📵", 1, "2026-03-05T15:00:00", 1,  1),
        (6,  "Marathon",         "Study for 2 hours in a single session",       "Session duration >= 7200s",      "⏱️", 1, "2026-03-09T11:15:00", 1,  1),
        (7,  "Perfect Session",  "Score 95+ in a session",                      "Score >= 95",                    "⭐", 1, "2026-03-07T11:30:00", 1,  1),
        (8,  "Century",          "Earn 1000 exp total",                         "Total exp >= 1000",              "💯", 0, None,                   770, 1000),
        (9,  "Coin Collector",   "Earn 200 coins total",                        "Total coins >= 200",             "🪙", 0, None,                   177, 200),
        (10, "Early Bird",       "Start a session before 9am",                  "Session start_time hour < 9",    "🌅", 1, "2026-03-06T08:30:00", 1,  1),
    ]
    conn.executemany('''
        INSERT INTO achievements VALUES (?,?,?,?,?,?,?,?,?)
    ''', achievements)


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    create_tables(conn)
    seed_sessions(conn)
    seed_user_stats(conn)
    seed_events(conn)
    seed_achievements(conn)

    conn.commit()
    conn.close()
    print(f"Mock database created at: {DB_PATH}")


if __name__ == "__main__":
    main()
