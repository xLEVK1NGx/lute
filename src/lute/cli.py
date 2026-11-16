import sys
from warnings import filterwarnings, resetwarnings
from pathlib import Path
import importlib
import inspect
import pkgutil
from rich import print
from lute.config import Config
from lute.plugins.base import Plugin
from lute.theme import Theme
import lute.plugins

config = 0
active_plugins = []

def main():
    global config
    config_path = Path()
    themes_path = config_path / "themes"
    config = Config.load()

    active_plugins = None

    # actual cli
    argv = sys.argv
    argc = len(argv)
    # 'lute list' to list all available/installed themes
    if argc == 1:
        print("type [green]'lute help'[/green] for help")
        return
    if argv[1] == "help":
        lute_help()
        return
    if argv[1] == "set" and argc == 3:
        lute_set(argv[2])

    if argv[1] == "list" and argv[2] == "themes":
        lute_list_themes()
        return




def lute_help():
    """Explain the program's purpose and list commands."""
    print(r"""
    [green]lute list [/]
        [default]list installed themes (found in .config/lute/themes/) [/]

    [green]lute set \[theme] \[--light-mode / --dark-mode] [/]
        [default]load the specified theme or set it to be the light-mode / dark-mode theme by default [/]

    [green]lute darken / lute lighten [/]
        [default]make the theme a lighter or darker shade, for supported themes (e.g. Catpuccin ) [/]

    [green]lute dark / lute light [/]
        [default]switch the theme to light / dark mode [/]

    [green]lute refresh \[app] [/]
        [default]refresh all lute-supported apps to apply theme. The [app] argument refreshes a specific app, e.g. hyprland. [/]

    [green]lute try \[theme] [/]
        [default]"try on" a theme. is faster than 'set' but potentially has bugs and/or other issues. [/]

    [green]lute apps [/] 
        [default]list all apps supported by lute, and whether they are installed and plugged in [/]

    [green]lute plug \[app] [/]
        [default]help with "plugging-in" an app [/]

    [green]lute config [/]
        [default]change lute's own settings [/]

    [green]lute new [/]
        [default]start the theme creation wizard to create your own theme (very basic. advanced themes require manual tinkering with the jsonc file.) [/]

    [green]lute install \[theme / url] [/]
        [default]if given a theme name, will try to find a theme with this name in LUTE's official repo and install it.
        if given a url, will install the theme from there. (warning: file MUST be prefixed with 'lute-', for example 'lute-nord.jsonc') [/]

""")


def lute_list_themes():
    """List installed themes and basic info about them in a table with:
    Name, Main color, Description, Preview screenshot, Tags (need to
    define those later) (Spacious, Compact, Orange, Pink, Pastel,
    Vibrant, Calm, Aggressive, Elegant, etc etc etc...).
    """
    pass


def lute_set(theme_name, light_mode=False, dark_mode=False):
    """Set theme to theme_name.jsonc. This implies:
        1. for each supported app, export a 'lute_values.extension' file,
           where extension can be anything from lua (Hyprland) to json
           (FastFetch?) or qml (quickshell)
        2. launch commands to "refresh" said apps, e.g. `hyprctl reload`
           or `qs refresh-config`

    The arguments will be added with luted, to manage light/dark mode on
    the desktop. "Which mode to use" is 'calculated' by luted, "SWITCH TO
    DARK MODE NOW" is lute's work.
    """
    global config
    config.select_theme(theme_name)
    print(r"Loading [yellow]" + theme_name + r".jsonc[default] ...")
    theme = Theme.load()

    plugin_classes = []

    for module_info in pkgutil.iter_modules(lute.plugins.__path__):
        if module_info.ispkg or module_info.name == "base":
            continue

        module = importlib.import_module(
            f"lute.plugins.{module_info.name}"
        )

        for _, cls in inspect.getmembers(module, inspect.isclass):
            if ( issubclass(cls, Plugin)  and  cls is not Plugin  and  cls.__module__ == module.__name__ ):
                plugin_classes.append(cls)

    plugins = [plugin_class() for plugin_class in plugin_classes]

    for plugin in plugins:
        if config.enabled_plugins.get(plugin.name, False) and plugin.detect(): 
            if plugin.is_plugged_in():
                print(plugin.name + " is active!")
                if config.ez_mode:
                    print("ez mode is not supported yet")
                    return # remove when ez mode is supported :P
                    print(r"[default]Generating ez overrides for [yellow]" + plugin.name + r"[default]...")
                    plugin.generate_overrides(theme)
                    plugin.refresh()
                else:
                    print(r"[default]Generating values for [yellow]" + plugin.name + r"[default]...")
                    plugin.generate_variables(theme)
                    plugin.refresh()
            else:
                if config.ez_mode:
                    plugin.help_install(ez_mode=True)
                else:
                    plugin.help_install(ez_mode=False)

    print(r"[default]Done!~ [green]" + theme.metadata.name + r"[default] loaded successfully! :3")


def lute_darken():
    """Change the variant of the theme to its darker version (indicated
    in metadata by "darker-ver" and/or "darkest-ver"). Most themes will
    have a binary dark/light system, but some (like Catppuccin or my own
    theme later) can have more levels.
    """
    pass


def lute_lighten():
    """Change the variant of the theme to its lighter version (indicated
    in metadata by "lightest-ver" and/or "lighter-ver"). Most themes will
    have a binary dark/light system, but some (like Catppuccin or my own
    theme later) can have more levels.
    """
    pass


def lute_dark():
    """Switch the theme to its dark variant."""
    pass


def lute_light():
    """Switch the theme to its light variant."""
    pass


def lute_refresh(app=None):
    """Relaunch "refresh"-type commands, like `hyprctl reload`.

    The `app` argument allows refreshing a specific app, e.g.
    `lute refresh --kitty`.
    """
    pass


def lute_try(theme_name):
    """Try on a theme. Doesn't do the deepest integration level, does
    just the most obvious things, and `lute stop` makes it go back to
    as it was.

    This is supposed to be "set" but faster. If "set" is fast enough by
    itself (<500ms), we can just reuse that...

    Can be used in a theme-picker app that's supposed to be fast, like
    the dynamic colors from the wallpaper on soramane's Quickshell config.
    """
    pass


def lute_list_apps():
    """List supported apps, in a table with columns:
        1. Supported app name
        2. App present / absent
        3. Lute 'Plugged-in' / is yet to be configured
        4. Lute actively changing app's appearance / app is still doing
           its own thing
    """
    pass


def lute_plug(app):
    """Show user step-by-step tutorial on how to use lute in the `app`
    of their choice.
    """
    pass


def lute_config():
    """TUI to change lute's own options, such as "wm managed by lute"
    to toggle options such as "border width", "corner radius", "gaps",
    etc.

    For testing, shall only open .config/lute/config.jsonc in $EDITOR.
    """
    pass


def lute_new():
    """Start the theme creation wizard to create your own theme (very
    basic. Advanced themes require manual tinkering with the jsonc file).
    """
    pass


def lute_install(theme_or_url):
    """If given a theme name, will try to find a theme with this name
    in LUTE's official repo and install it.

    If given a URL, will install the theme from there. (Warning: file
    MUST be prefixed with "lute-...").
    """
    pass
