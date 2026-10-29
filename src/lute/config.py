import os
import shutil
from pathlib import Path
import json5 as json

class Config():
    def xdg_config_home() -> Path:
        """Return $XDG_CONFIG_HOME or the default ~/.config."""
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            return Path(xdg)
        return Path.home() / ".config"

    config_file = xdg_config_home() / "lute" / "config.jsonc"
    
    if not config_file.exists():
        with open(config_file) as cf: 
            cf.write("")

    def load_config():
        with open(config_file) as cf:
            config_dict = json.load()
