"""Helper utilities for metric formatting and dataset parsing."""

from typing import Dict, List, Any


def format_observation_labels(kb, obs_ids: List[str]) -> List[str]:
    """Translates observation IDs into human-readable labels."""
    categories = kb.get_indicator_categories()
    lookup = {}
    for cat, items in categories.items():
        for item in items:
            lookup[item["id"]] = f"[{cat}] {item['name']}"
    return [lookup.get(oid, oid) for oid in obs_ids]