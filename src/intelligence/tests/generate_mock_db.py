# Generates mock_data.db — a fake SQLite database for UI development

import os
import sys

try:
    from database import Database
except ModuleNotFoundError:
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
    from database import Database

DB_PATH = os.path.join(os.path.dirname(__file__), "mock_data.db")


def reset_tables(conn):
    # Clear seeded tables so a fresh mock dataset can be rebuilt deterministically
    conn.execute("DELETE FROM events")
    conn.execute("DELETE FROM achievements")
    conn.execute("DELETE FROM sessions")
    conn.execute("DELETE FROM user_stats")
    conn.execute(
        "DELETE FROM sqlite_sequence WHERE name IN ('sessions', 'events', 'achievements')"
    )


def seed_sessions(conn):
    sessions = [
        # id, start_time, end_time, duration, focused_time, events, time_away,
        # look_away_time, distraction_time, phone, look_away, left_desk, app, idle,
        # focus_pct, score, points, coins, enabled_distractions
        (1,  "2026-03-04T09:00:00", "2026-03-04T10:30:00", 5400, 4212, 6, 180, 300, 908,  1, 2, 1, 1, 1, 78.0, 82, 120, 30, None),
        (2,  "2026-03-05T14:00:00", "2026-03-05T15:00:00", 3600, 3060, 3, 60,  120, 360,  0, 1, 0, 2, 0, 85.0, 91, 95,  20, None),
        (3,  "2026-03-06T08:30:00", "2026-03-06T09:45:00", 4500, 3150, 9, 300, 420, 1050, 3, 3, 1, 2, 0, 70.0, 65, 80,  15, None),
        (4,  "2026-03-07T10:00:00", "2026-03-07T11:30:00", 5400, 5130, 2, 30,  60,  210,  0, 1, 0, 1, 0, 95.0, 98, 150, 40, None),
        (5,  "2026-03-08T13:00:00", "2026-03-08T13:45:00", 2700, 1890, 5, 240, 180, 630,  2, 1, 1, 1, 0, 70.0, 60, 55,  10, None),
        (6,  "2026-03-09T09:15:00", "2026-03-09T11:15:00", 7200, 6480, 4, 120, 300, 420,  1, 2, 0, 1, 0, 90.0, 94, 200, 50, None),
        (7,  "2026-03-10T15:00:00", "2026-03-10T16:00:00", 3600, 2520, 7, 360, 240, 840,  2, 2, 1, 2, 0, 70.0, 63, 70,  12, None),
        (8,  "2026-03-11T08:00:00", "2026-03-11T09:00:00", 3600, 3240, 3, 60,  90,  270,  0, 1, 1, 1, 0, 90.0, 89, 90,  22, None),
        (9,  "2026-03-12T16:00:00", "2026-03-12T17:30:00", 5400, 3780, 8, 300, 420, 1260, 2, 3, 1, 2, 0, 70.0, 58, 60,  12, None),
        (10, "2026-03-13T10:30:00", "2026-03-13T12:00:00", 5400, 4860, 3, 90,  150, 360,  0, 1, 1, 1, 0, 90.0, 92, 140, 35, None),
        (11, "2026-03-14T07:45:00", "2026-03-14T08:30:00", 2700, 2430, 2, 30,  60,  180,  0, 1, 0, 1, 0, 90.0, 88, 75,  18, None),
        (12, "2026-03-15T13:30:00", "2026-03-15T15:00:00", 5400, 4050, 7, 240, 360, 1050, 1, 3, 1, 2, 0, 75.0, 70, 85,  18, None),
        (13, "2026-03-16T09:00:00", "2026-03-16T10:00:00", 3600, 3420, 2, 30,  60,  120,  0, 1, 0, 1, 0, 95.0, 96, 110, 28, None),
        (14, "2026-03-17T15:30:00", "2026-03-17T16:15:00", 2700, 1890, 6, 180, 240, 630,  2, 2, 1, 1, 0, 70.0, 55, 45,  8,  None),
        (15, "2026-03-18T10:00:00", "2026-03-18T11:30:00", 5400, 4860, 3, 60,  120, 360,  0, 1, 1, 1, 0, 90.0, 93, 145, 38, None),
        (16, "2026-03-19T20:00:00", "2026-03-19T21:00:00", 3600, 2520, 5, 240, 300, 840,  1, 2, 1, 1, 0, 70.0, 62, 65,  13, None),
        (17, "2026-03-20T09:30:00", "2026-03-20T11:00:00", 5400, 5130, 2, 30,  60,  180,  0, 1, 0, 1, 0, 95.0, 97, 155, 42, None),
        (18, "2026-03-21T14:00:00", "2026-03-21T15:30:00", 5400, 4320, 5, 180, 240, 720,  1, 2, 1, 1, 0, 80.0, 78, 100, 24, None),
        (19, "2026-03-22T08:15:00", "2026-03-22T09:30:00", 4500, 4050, 3, 60,  120, 300,  0, 1, 1, 1, 0, 90.0, 90, 115, 30, None),
        (20, "2026-03-23T11:00:00", "2026-03-23T12:30:00", 5400, 4590, 4, 120, 180, 540,  1, 1, 1, 1, 0, 85.0, 85, 130, 32, None),
    ]
    conn.executemany('''
        INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', sessions)


def seed_user_stats(conn):
    conn.execute('''
        INSERT OR REPLACE INTO user_stats VALUES (
            1, 19, 3779.1, 20, 90900, 497, 2085, 89, 32, 'fox',
            '2026-03-04T09:00:00', '2026-03-23T12:30:00'
        )
    ''')


def seed_events(conn):
    events = [
        # session 1
        (1,  1, "phone_distraction",     "2026-03-04T09:22:00", 45,  "Phone screen lit up"),
        (2,  1, "look_away_distraction", "2026-03-04T09:45:00", 30,  None),
        (3,  1, "app_distraction",       "2026-03-04T10:01:00", 120, "YouTube opened"),
        (4,  1, "look_away_distraction", "2026-03-04T10:10:00", 20,  None),
        (5,  1, "left_desk_distraction", "2026-03-04T10:18:00", 180, "Left desk"),
        (6,  1, "idle_distraction",      "2026-03-04T10:25:00", 60,  "No input detected"),
        # session 2
        (7,  2, "look_away_distraction", "2026-03-05T14:15:00", 25,  None),
        (8,  2, "app_distraction",       "2026-03-05T14:40:00", 90,  "Discord opened"),
        (9,  2, "app_distraction",       "2026-03-05T14:55:00", 60,  "Discord opened again"),
        # session 4 (best session)
        (10, 4, "look_away_distraction", "2026-03-07T10:45:00", 30,  None),
        (11, 4, "app_distraction",       "2026-03-07T11:20:00", 60,  "Twitter opened"),
        # session 6 (longest session)
        (12, 6, "phone_distraction",     "2026-03-09T09:50:00", 40,  "Phone notification"),
        (13, 6, "look_away_distraction", "2026-03-09T10:15:00", 90,  None),
        (14, 6, "look_away_distraction", "2026-03-09T10:45:00", 45,  None),
        (15, 6, "app_distraction",       "2026-03-09T11:05:00", 120, "Spotify opened"),
        # session 8
        (16, 8,  "look_away_distraction", "2026-03-11T08:20:00", 30,  None),
        (17, 8,  "left_desk_distraction", "2026-03-11T08:35:00", 60,  "Left desk"),
        (18, 8,  "app_distraction",       "2026-03-11T08:50:00", 90,  "Reddit opened"),
        # session 9
        (19, 9,  "phone_distraction",     "2026-03-12T16:15:00", 60,  "Phone call"),
        (20, 9,  "look_away_distraction", "2026-03-12T16:30:00", 45,  None),
        (21, 9,  "phone_distraction",     "2026-03-12T16:45:00", 30,  "Phone notification"),
        (22, 9,  "look_away_distraction", "2026-03-12T17:00:00", 60,  None),
        (23, 9,  "left_desk_distraction", "2026-03-12T17:05:00", 120, "Left desk"),
        (24, 9,  "look_away_distraction", "2026-03-12T17:10:00", 30,  None),
        (25, 9,  "app_distraction",       "2026-03-12T17:15:00", 90,  "Discord opened"),
        (26, 9,  "app_distraction",       "2026-03-12T17:20:00", 60,  "YouTube opened"),
        # session 10
        (27, 10, "look_away_distraction", "2026-03-13T11:00:00", 30,  None),
        (28, 10, "left_desk_distraction", "2026-03-13T11:20:00", 90,  "Bathroom break"),
        (29, 10, "app_distraction",       "2026-03-13T11:45:00", 60,  "Slack opened"),
        # session 11
        (30, 11, "look_away_distraction", "2026-03-14T08:00:00", 30,  None),
        (31, 11, "app_distraction",       "2026-03-14T08:15:00", 60,  "Email opened"),
        # session 12
        (32, 12, "phone_distraction",     "2026-03-15T13:45:00", 45,  "Phone notification"),
        (33, 12, "look_away_distraction", "2026-03-15T14:00:00", 60,  None),
        (34, 12, "look_away_distraction", "2026-03-15T14:15:00", 45,  None),
        (35, 12, "left_desk_distraction", "2026-03-15T14:25:00", 120, "Snack break"),
        (36, 12, "look_away_distraction", "2026-03-15T14:35:00", 30,  None),
        (37, 12, "app_distraction",       "2026-03-15T14:40:00", 60,  "Twitter opened"),
        (38, 12, "app_distraction",       "2026-03-15T14:50:00", 45,  "YouTube opened"),
        # session 13
        (39, 13, "look_away_distraction", "2026-03-16T09:30:00", 30,  None),
        (40, 13, "app_distraction",       "2026-03-16T09:45:00", 45,  "Slack opened"),
        # session 14
        (41, 14, "phone_distraction",     "2026-03-17T15:40:00", 60,  "Phone call"),
        (42, 14, "phone_distraction",     "2026-03-17T15:55:00", 30,  "Phone notification"),
        (43, 14, "look_away_distraction", "2026-03-17T16:00:00", 45,  None),
        (44, 14, "look_away_distraction", "2026-03-17T16:05:00", 30,  None),
        (45, 14, "left_desk_distraction", "2026-03-17T16:08:00", 180, "Left desk"),
        (46, 14, "app_distraction",       "2026-03-17T16:12:00", 60,  "Discord opened"),
        # session 15
        (47, 15, "look_away_distraction", "2026-03-18T10:30:00", 30,  None),
        (48, 15, "left_desk_distraction", "2026-03-18T10:50:00", 60,  "Bathroom break"),
        (49, 15, "app_distraction",       "2026-03-18T11:15:00", 45,  "Slack opened"),
        # session 16
        (50, 16, "phone_distraction",     "2026-03-19T20:15:00", 45,  "Phone notification"),
        (51, 16, "look_away_distraction", "2026-03-19T20:30:00", 60,  None),
        (52, 16, "look_away_distraction", "2026-03-19T20:40:00", 45,  None),
        (53, 16, "left_desk_distraction", "2026-03-19T20:48:00", 120, "Left desk"),
        (54, 16, "app_distraction",       "2026-03-19T20:55:00", 60,  "YouTube opened"),
        # session 17
        (55, 17, "look_away_distraction", "2026-03-20T10:00:00", 30,  None),
        (56, 17, "app_distraction",       "2026-03-20T10:30:00", 45,  "Slack opened"),
        # session 18
        (57, 18, "phone_distraction",     "2026-03-21T14:20:00", 40,  "Phone notification"),
        (58, 18, "look_away_distraction", "2026-03-21T14:40:00", 60,  None),
        (59, 18, "look_away_distraction", "2026-03-21T15:00:00", 30,  None),
        (60, 18, "left_desk_distraction", "2026-03-21T15:10:00", 90,  "Coffee break"),
        (61, 18, "app_distraction",       "2026-03-21T15:20:00", 60,  "Discord opened"),
        # session 19
        (62, 19, "look_away_distraction", "2026-03-22T08:45:00", 30,  None),
        (63, 19, "left_desk_distraction", "2026-03-22T09:00:00", 60,  "Bathroom break"),
        (64, 19, "app_distraction",       "2026-03-22T09:15:00", 45,  "Email opened"),
        # session 20
        (65, 20, "phone_distraction",     "2026-03-23T11:15:00", 30,  "Phone notification"),
        (66, 20, "look_away_distraction", "2026-03-23T11:30:00", 45,  None),
        (67, 20, "left_desk_distraction", "2026-03-23T11:50:00", 90,  "Snack break"),
        (68, 20, "app_distraction",       "2026-03-23T12:10:00", 60,  "Twitter opened"),
    ]
    conn.executemany('''
        INSERT INTO events VALUES (?,?,?,?,?,?)
    ''', events)


def seed_achievements(conn):
    achievements = [
        # id, name, desc, criteria, emoji, unlocked, unlocked_at, progress, target
        (1,  "First Focus",      "Complete your first study session",           "Complete 1 session",             "🎯", 1, "2026-03-04T10:30:00", 1,  1),
        (2,  "On a Roll",        "Complete 5 sessions",                         "Complete 5 sessions",            "🔥", 1, "2026-03-08T13:45:00", 5,  5),
        (3,  "Dedicated",        "Complete 10 sessions",                        "Complete 10 sessions",           "💪", 1, "2026-03-13T12:00:00",  20, 10),
        (4,  "Sharp Focus",      "Achieve 90%+ focus in a session",             "Focus percentage >= 90",         "🧠", 1, "2026-03-07T11:30:00", 1,  1),
        (5,  "Phone Away",       "Complete a session with zero phone distractions", "0 phone distractions",      "📵", 1, "2026-03-05T15:00:00", 1,  1),
        (6,  "Marathon",         "Study for 2 hours in a single session",       "Session duration >= 7200s",      "⏱️", 1, "2026-03-09T11:15:00", 1,  1),
        (7,  "Perfect Session",  "Score 95+ in a session",                      "Score >= 95",                    "⭐", 1, "2026-03-07T11:30:00", 1,  1),
        (8,  "Century",          "Earn 1000 exp total",                         "Total exp >= 1000",              "💯", 1, "2026-03-18T11:30:00",  2085, 1000),
        (9,  "Coin Collector",   "Earn 200 coins total",                        "Total coins >= 200",             "🪙", 1, "2026-03-17T16:15:00",  497,  200),
        (10, "Early Bird",       "Start a session before 9am",                  "Session start_time hour < 9",    "🌅", 1, "2026-03-06T08:30:00", 1,  1),
    ]
    conn.executemany('''
        INSERT INTO achievements VALUES (?,?,?,?,?,?,?,?,?)
    ''', achievements)


def create_mock_database(db_path: str = DB_PATH) -> str:
    # Create a fresh mock database using the production schema and seeded UI data
    if os.path.exists(db_path):
        os.remove(db_path)

    db = Database(db_path=db_path)
    conn = db._get_connection()

    try:
        reset_tables(conn)
        seed_sessions(conn)
        seed_user_stats(conn)
        seed_events(conn)
        seed_achievements(conn)
        conn.commit()
    finally:
        db.close()

    return db_path


def main():
    db_path = create_mock_database()
    print(f"Mock database created at: {db_path}")


if __name__ == "__main__":
    main()
