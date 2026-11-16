import os
from pathlib import Path
from importlib.resources import files, as_file
import json5 as json
from dataclasses import dataclass
import re

def xdg_config_home() -> Path:
    """Return $XDG_CONFIG_HOME or the default ~/.config."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return Path(xdg) if xdg else Path.home() / ".config"

LUTE_DIR = xdg_config_home() / "lute"

THEMES_DIR = LUTE_DIR / "themes" 
CONFIG_FILE = LUTE_DIR / "config.jsonc"

def ensure_config():
    if not CONFIG_FILE.exists():
        LUTE_DIR.mkdir(parents=True, exist_ok=True)
        src = files("lute").joinpath("config.jsonc")
        CONFIG_FILE.write_text(src.read_text())

def load_config():
    with open(CONFIG_FILE) as cf:
        return json.load(cf)


@dataclass
class Config():
    lute_dir: Path
    themes_dir: Path

    selected_theme: str
    ez_mode: bool
    enabled_plugins: dict[str, bool]

    verbose: bool = False

    @classmethod
    def load(cls) -> "Config":
        loaded = load_config()
        return cls(
            lute_dir = LUTE_DIR,
            themes_dir = THEMES_DIR,

            selected_theme = loaded["selected_theme"],
            ez_mode = loaded["ez_mode"],
            enabled_plugins = loaded["enabled_plugins"]
                )

    def select_theme(self, theme_name: str):
        with CONFIG_FILE.open("r", encoding="utf-8", newline="") as file:
            text = file.read()

        pattern = re.compile(
            r'^([ \t]*"selected_theme"[ \t]*:[ \t]*)'
            r'"(?:\\.|[^"\\])*"',
            re.MULTILINE,
        )

        matches = list(pattern.finditer(text))

        if len(matches) != 1:
            raise ValueError(
                f"Expected one selected_theme field, found {len(matches)}"
            )

        match = matches[0]
        new_value = json.dumps(theme_name, ensure_ascii=False)

        # keep the field name and spacing
        updated = text[:match.end(1)] + new_value + text[match.end():]

        with CONFIG_FILE.open("w", encoding="utf-8", newline="") as file:
            file.write(updated)
        self.selected_theme = theme_name

