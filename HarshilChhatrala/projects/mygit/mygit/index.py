import json
from pathlib import Path

INDEX_PATH = Path(".mygit/index")


def read_index() -> dict:
    """Reads the staging index. Returns a dict mapping path -> sha1."""
    if not INDEX_PATH.exists():
        return {}
    with open(INDEX_PATH, "r") as f:
        return json.load(f)


def write_index(index_data: dict):
    """Writes the current dict back to the staging index file."""
    with open(INDEX_PATH, "w") as f:
        json.dump(index_data, f, indent=4)