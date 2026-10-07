"""`.claude-plugin/marketplace.json` helpers. Output round-trips the existing file byte-for-byte (indent=2)."""
import json
from pathlib import Path

PATH = Path(".claude-plugin/marketplace.json")


def load(lib: Path) -> dict:
    return json.loads((lib / PATH).read_text())


def save(lib: Path, data: dict) -> None:
    (lib / PATH).write_text(json.dumps(data, indent=2) + "\n")


def bundle_names(data: dict) -> list[str]:
    return [p["name"] for p in data.get("plugins", [])]


def bundled_skills(data: dict) -> set[str]:
    return {s.rsplit("/", 1)[-1] for p in data.get("plugins", []) for s in p.get("skills", [])}


def add_to_bundle(data: dict, bundle: str, names: list[str], description: str = "") -> None:
    """Append `./skills/<name>` to the bundle, creating it when missing. Mutates `data`."""
    plugin = next((p for p in data["plugins"] if p["name"] == bundle), None)
    if plugin is None:
        plugin = {"name": bundle, "description": description, "source": "./", "strict": False, "skills": []}
        data["plugins"].append(plugin)
    for n in names:
        if f"./skills/{n}" not in plugin["skills"]:
            plugin["skills"].append(f"./skills/{n}")
