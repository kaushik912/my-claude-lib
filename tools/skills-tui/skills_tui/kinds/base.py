"""The extension seam: a Kind knows how to list, detect, add and remove one type of lib item."""
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

import yaml


@dataclass(frozen=True)
class Item:
    kind: str
    name: str
    description: str
    origin: str  # "mine" | "vendored"

    @property
    def key(self) -> str:
        return f"{self.kind}/{self.name}"


@dataclass(frozen=True)
class Ctx:
    project: Path
    lib: Path
    agent: str = "claude-code"
    global_: bool = False
    exec_: Callable = subprocess.run  # injectable for tests


@dataclass(frozen=True)
class Action:
    label: str
    run: Callable[[], int]  # returns exit code


class Kind(Protocol):
    name: str

    def catalog(self, lib: Path) -> list[Item]: ...
    def installed(self, project: Path) -> set[str]: ...  # bare names
    def add(self, names: tuple[str, ...], ctx: Ctx) -> list[Action]: ...
    def remove(self, names: tuple[str, ...], ctx: Ctx) -> list[Action]: ...


def frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data = yaml.safe_load(parts[1])
    return data if isinstance(data, dict) else {}
