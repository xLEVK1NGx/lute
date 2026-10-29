import os
from pathlib import Path
from importlib.resources import files, as_file
import json5 as json


def xdg_config_home() -> Path:
    """Return $XDG_CONFIG_HOME or the default ~/.config."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return Path(xdg) if xdg else Path.home() / ".config"

LUTE_DIR = xdg_config_home()

THEMES_DIR = LUTE_DIR / "themes" 
CONFIG_FILE = LUTE_DIR / "config.jsonc"

if not CONFIG_FILE.exists():
    src = files("lute").joinpath("config.jsonc")
    CONFIG_FILE.write_text(src.read_text())

def load_config():
    with open(CONFIG_FILE) as cf:
        config_dict = json.load()


class Config():
    pass
