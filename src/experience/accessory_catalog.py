from pathlib import Path

_STATIC = Path(__file__).resolve().parent / "static"
_ACCESSORIES_DIR = _STATIC / "pets" / "accessories"

# Layered sprite overlay catalog.
#
# Keys in ACCESSORY_CATALOG are the stable accessory ids stored in the
# database (inventory.item_id and user_stats.equipped_accessories).
#
# Each entry has:
#   name            - display name shown in the UI
#   slot            - equipment slot this item occupies ("hat", "glasses", ...).
#                     Only one accessory per slot can be equipped at a time.
#   sprite          - absolute path to the accessory PNG
#   cost            - price in coins
#   z_index         - draw order on the composed pixmap (higher = on top)
#   anchor_ratio    - (rx, ry) fractional point INSIDE the accessory's
#                     CONTENT rect (the tight alpha bounding box of the
#                     visible hat, ignoring transparent PNG padding) that
#                     snaps to the pet's slot anchor.  (0.5, 1.0) is the
#                     bottom-center of the hat and is the default for hats.
#   scale_ratio     - visible hat width divided by the visible pet width
#                     (e.g. 0.4 => the actual hat graphic is 40% as wide
#                     as the actual pet body).  Robust to differing amounts
#                     of PNG padding across sprites.
#   compatible_pets - optional list of pet ids this item can be equipped on;
#                     omit or set to None for "works on every pet".

ACCESSORY_CATALOG: dict[str, dict] = {
    "crown": {
        "name": "Crown",
        "slot": "hat",
        "sprite": str(_ACCESSORIES_DIR / "Crown.png"),
        "cost": 0,
        "z_index": 20,
        "anchor_ratio": (0.5, 1.0),
        "scale_ratio": 0.35,
    },
    "top_hat": {
        "name": "Top Hat",
        "slot": "hat",
        "sprite": str(_ACCESSORIES_DIR / "TopHat.png"),
        "cost": 0,
        "z_index": 20,
        "anchor_ratio": (0.5, 1.0),
        "scale_ratio": 0.35,
    },
    "cop_hat": {
        "name": "Police Hat",
        "slot": "hat",
        "sprite": str(_ACCESSORIES_DIR / "CopHat.png"),
        "cost": 0,
        "z_index": 20,
        "anchor_ratio": (0.5, 1.0),
        "scale_ratio": 0.45,
    },
    "pirate_hat": {
        "name": "Pirate Hat",
        "slot": "hat",
        "sprite": str(_ACCESSORIES_DIR / "PirateHat.png"),
        "cost": 0,
        "z_index": 20,
        "anchor_ratio": (0.5, 1.0),
        "scale_ratio": 0.5,
    },
}
