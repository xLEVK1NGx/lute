import lute.config as config

class Plugin():
    """ Base class for all plugins """
    name: str 
    version: str

    def detect(self) -> bool:
        """ Detects whether the app is installed """
        raise NotImplementedError

    def is_plugged_in(self) -> bool:
        """ Detects if the app is plugged in """
        raise NotImplementedErr

    def generate_variables(self, theme: Theme) -> None:
        """ Generates the lute variables in the app's supported format, to be 
        imported at the TOP of a config and used as variables """
        raise NotImplementedError

    def generate_overrides(self, theme: Theme) -> None:
        """ Generates lute theme-based overrides to import at the BOTTOM of a
        config """
        raise NotImplementedError

    def refresh(self) -> None:
        """ Refresh the app to apply the config. Should NEVER close and reopen
        the app, this is only intended for a dynamic reloading """
        raise NotImplementedError

    def help_install(self) -> None:
        """ Display help messages to guide the user to installing the plugin
        for the app """ 
        raise NotImplementedError
