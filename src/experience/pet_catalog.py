from pathlib import Path

_STATIC = Path(__file__).resolve().parent / "static"

PET_CATALOG: dict[str, dict] = {
    "cat": {
        "name": "Calico Cat",
        "sprite": str(_STATIC / "pets" / "cat" / "Cat.png"),
        "cost": 0,
    },
    "dog": {
        "name": "Pup",
        "sprite": str(_STATIC / "pets" / "dog" / "Dog.png"),
        "cost": 10,
    },
    "frog": {
        "name": "Frog",
        "sprite": str(_STATIC / "pets" / "frog" / "Frog.png"),
        "cost": 5,
    },
}

DEFAULT_PET = "cat"
