import lute.config as config
from lute.plugins.base import Plugin
from lute.theme import Theme
import subprocess
from rich import print

class KittyPlugin(Plugin):
    """ Kitty terminal plugin """
    display_name = "kitty"
    name = "kitty"
    version = "1.0.0"


    def detect(self) -> bool:
        if subprocess.run("ls /usr/share/applications/kitty.desktop > /dev/null 2>&1", shell=True).returncode == 0:
            return True
        return False

    def is_plugged_in(self) -> bool:
        path = config.xdg_config_home() / "kitty" / "kitty.conf"
        if not path.exists():
            return False
        with path.open(encoding="utf-8") as kitty_config:
            for line in kitty_config:
                if line.strip() == 'include lute-generated.conf':
                    return True
        return False

    def generate_variables(self, theme) -> None:
        path = config.xdg_config_home() / "kitty" / "lute-generated.conf"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as lgf: #lgf = Lute-Generated File
            term = theme.colors.terminal
            font = theme.fonts

            lgf.write("# === TEXT ===\n")
            lgf.write(f"foreground {term.foreground}\n")
            lgf.write(f"background {term.background}\n")
            lgf.write(f"selection_foreground {term.selection.foreground}\n")
            lgf.write(f"selection_background {term.selection.background}\n")

            lgf.write("# === COLORS ===\n")
            for index in range(16):
                color = getattr(term.ansi, str(index))
                lgf.write(f"color{index} {color}\n")
            lgf.write(f"url_color {term.url}\n")
            lgf.write(f"background_opacity {term.background_opacity}\n")

            lgf.write("# === TABS ===\n")
            lgf.write(f"active_tab_foreground {term.tabs.active_foreground}\n")
            lgf.write(f"active_tab_background {term.tabs.active_background}\n")
            lgf.write(f"inactive_tab_foreground {term.tabs.inactive_foreground}\n")
            lgf.write(f"inactive_tab_background {term.tabs.inactive_background}\n")

            lgf.write("# === FONTS ===\n")
            lgf.write(f"font_family family='{font.monospace.family}'\n")
            lgf.write(f"bold_font family='{font.monospace.family}'\n")
            lgf.write(f"italic_font family='{font.monospace.family}'\n")
            lgf.write(f"bold_italic_font family='{font.monospace.family}'\n")
            lgf.write(f"font_size {font.monospace.sizes.base}\n")



    def generate_overrides(self, theme) -> None:
        self.generate_variables(theme)

    def refresh(self, quiet=True) -> None:
        if quiet:
            subprocess.run("kill -USR1 $(pidof kitty) > /dev/null 2>&1", shell=True)
        else:
            subprocess.run("kill -USR1 $(pidof kitty)", shell=True)

    def help_install(self, ez_mode) -> None:
        if ez_mode:
            print("ez mode is not supported yet!")
        else:
            print(r"""[white]To plug in kitty you need to add [yellow]'include lute-generated.conf'[/] to the top of your kitty.conf. Don't forget to remove or comment out any later color overrides you might've left in the config :3""")
