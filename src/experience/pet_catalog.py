from pathlib import Path

_STATIC = Path(__file__).resolve().parent / "static"

# Each pet entry has:
#   name         - display name
#   sprite       - absolute path to the pet PNG
#   cost         - price in coins
#   slot_anchors - fractional (rx, ry) point inside the pet's CONTENT rect
#                  (the tight alpha bounding box of the visible artwork)
#                  where each equipment slot anchors.  Transparent padding
#                  around the sprite is ignored so values are stable even
#                  if the PNG has extra empty space.
#
#                  ry = 0 means "top of the visible pet".  For a hat we want
#                  the anchor at the top of the head; for cats/dogs with
#                  ears that stick up, the value sits slightly below the
#                  ear tips so the hat rests between the ears.

PET_CATALOG: dict[str, dict] = {
    "cat": {
        "name": "Calico Cat",
        "sprite": str(_STATIC / "pets" / "cat" / "Cat.png"),
        "cost": 0,
        "slot_anchors": {"hat": (0.37, 0.16)},
    },
    "dog": {
        "name": "Pup",
        "sprite": str(_STATIC / "pets" / "dog" / "Dog.png"),
        "cost": 0,
        "slot_anchors": {"hat": (0.5, 0.02)},
    },
    "frog": {
        "name": "Frog",
        "sprite": str(_STATIC / "pets" / "frog" / "Frog.png"),
        "cost": 0,
        "slot_anchors": {"hat": (0.5, 0.08)},
    },
    "panther": {
        "name": "Panther",
        "sprite": str(_STATIC / "pets" / "panther" / "Panther.png"),
        "cost": 0,
        "slot_anchors": {"hat": (0.5, 0.08)},
    },
}

DEFAULT_PET = "cat"

# Fallback slot anchors for pets that don't declare their own.
DEFAULT_SLOT_ANCHORS: dict[str, tuple[float, float]] = {
    "hat": (0.5, 0.05),
}
