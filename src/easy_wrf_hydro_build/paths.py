"""Case directory manager inspired by easy_vic_build's project layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class EwhbCase:
    cases_home: Path
    case_name: str

    @property
    def case_dir(self) -> Path:
        return self.cases_home / self.case_name

    def builddir(self) -> None:
        for folder in self.required_dirs():
            folder.mkdir(parents=True, exist_ok=True)

    def required_dirs(self) -> list[Path]:
        root = self.case_dir
        return [
            root,
            root / "build",
            root / "config",
            root / "domain",
            root / "forcing",
            root / "logs",
            root / "namelists",
            root / "output",
            root / "restart",
            root / "run",
            root / "scripts",
        ]
