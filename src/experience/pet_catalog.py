from pathlib import Path

_STATIC = Path(__file__).resolve().parent / "static"

PET_CATALOG: dict[str, dict] = {
    "panther": {
        "name": "Panther",
        "sprite": str(_STATIC / "pets" / "panther" / "Panther.png"),
        "cost": 0,
    },
    "cat": {
        "name": "Calico Cat",
        "sprite": str(_STATIC / "pets" / "cat" / "Cat.png"),
        "cost": 50,
    },
    "dog": {
        "name": "Pup",
        "sprite": str(_STATIC / "pets" / "dog" / "Dog.png"),
        "cost": 50,
    },
    "frog": {
        "name": "Frog",
        "sprite": str(_STATIC / "pets" / "frog" / "Frog.png"),
        "cost": 75,
    },
}

DEFAULT_PET = "panther"
