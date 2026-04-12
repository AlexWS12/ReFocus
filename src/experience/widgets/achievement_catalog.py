from pathlib import Path

_STATIC = Path(__file__).resolve().parent.parent / "static" / "pets" / "achievements"

ACHIEVMENT_CATALOG: dict[str,dict] = {
    "First Step": {
        "description": "Complete your first study session",
        "goal": 1,
        "icon": str(_STATIC / "First_Step.png")
    },
    "On A Roll": {
        "description": "Complete 3 sessions in a day",
        "goal": 3,
        "icon": str(_STATIC / "On_A_Roll.png")
    },
    "Grind Mode": {
        "description": "Study for 5 hours total",
        "goal": 18000,
        "icon": str(_STATIC / "Grind_Mode.png")
    },
    "Marathon": {
        "description": "Complete a 2 hour session",
        "goal": 2,
        "icon": str(_STATIC / "Marathon.png")
    },
    "Consistent": {
        "description": "Study 3 days in a row",
        "goal": 3,
        "icon": str(_STATIC / "Consistent.png")
    },
    "Dedicated": {
        "description": "Study 7 days in a row",
        "goal": 7,
        "icon": str(_STATIC / "Dedicated.png")
    },
    "Unstoppable": {
        "description": "Study 30 days in a row",
        "goal": 30,
        "icon": str(_STATIC / "Unstoppable.png")
    },
    "Level Up!": {
        "description": "Reach Level 5",
        "goal": 5,
        "icon": str(_STATIC / "Level_Up.png")
    },
    "Scholar": {
        "description": "Reach level 10",
        "goal": 10,
        "icon": str(_STATIC / "Scholar.png")
    },
    "XP Collector": {
        "description": "Earn 10,000Xp in total",
        "goal": 10000,
        "icon": str(_STATIC / "XP_Collector.png")
    },
    "Pet Lover": {
        "description": "Complete a study session with each pet",
        "goal": 3,
        "icon": str(_STATIC / "Pet_Lover.png")
    },
    "Night Lover": {
        "description": "Use the dark mode theme",
        "goal": 1,
        "icon": str(_STATIC / "Night_Lover.png")
    }
}