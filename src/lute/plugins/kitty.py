import lute.config as config
from lute.plugins.base import Plugin
import os
from rich import print

class KittyPlugin(Plugin):
    """ Kitty terminal plugin """
    name = "kitty"
    version = "0.1"


    def detect(self) -> bool:
        if os.system("ls /usr/share/applications/kitty.desktop > /dev/null 2>&1") == 0:
            return True
        return False

    def is_plugged_in(self) -> bool:
        path = config.xdg_config_home() / "kitty" / "kitty.conf"
        with path.open(encoding="utf-8") as kitty_config:
            for line in kitty_config:
                if line.strip() == 'include lute-generated.conf':
                    return True
        return False

    def generate_variables(self, theme) -> None:
        path = config.xdg_config_home() / "kitty" / "lute-generated.conf"
        with path.open("w", encoding="utf-8") as lute_generated:
            term = theme.colors.terminal
            font = theme.fonts

            lute_generated.write("# === TEXT ===\n")
            lute_generated.write(f"foreground {term.foreground}\n")
            lute_generated.write(f"background {term.background}\n")
            lute_generated.write(f"selection_foreground {term.selection.foreground}\n")
            lute_generated.write(f"selection_background {term.selection.background}\n")

            lute_generated.write("# === COLORS ===\n")
            for index in range(16):
                color = getattr(term.ansi, str(index))
                lute_generated.write(f"color{index} {color}\n")
            lute_generated.write(f"url_color {term.url}\n")
            lute_generated.write(f"background_opacity {term.background_opacity}\n")

            lute_generated.write("# === TABS ===\n")
            lute_generated.write(f"active_tab_foreground {term.tabs.active_foreground}\n")
            lute_generated.write(f"active_tab_background {term.tabs.active_background}\n")
            lute_generated.write(f"inactive_tab_foreground {term.tabs.inactive_foreground}\n")
            lute_generated.write(f"inactive_tab_background {term.tabs.inactive_background}\n")

            lute_generated.write("# === FONTS ===\n")
            lute_generated.write("# nothing here yet :^\n")




    def generate_overrides(self, theme) -> None:
        raise NotImplementedError

    def refresh(self) -> None:
        os.system("kill -USR1 $(pidof kitty) > /dev/null 2>&1")

    def help_install(self, ez_mode) -> None:
        if ez_mode:
            print("ez mode is not supported yet!")
        else:
            print(r"""[white]To plug in kitty you need to add [yellow]'include lute-generated.conf'[/] to the top of your kitty.conf. Don't forget to remove or comment out any later color overrides you might've left in the config :3""")
