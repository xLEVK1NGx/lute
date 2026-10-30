from lute.config import *
from importlib.resources import files, as_file
from dataclasses import *
from jsonschema import validate, Draft202012Validator
import json5 as json

config = Config.load()

def load_jsonc(path):
    with open(path, encoding="UTF-8") as file:
        return json.load(file)

def load_jsonc_validate(path: Path):
    # load schema
    with as_file(files("lute").joinpath("theme.schema.json")) as file:
        schema = load_jsonc(file) 
    # validate schema
    Draft202012Validator.check_schema(schema)
    # get theme data
    theme_data = load_jsonc(path)
    # validate the data with the schema
    validate(instance=theme_data, schema=schema)



@dataclass
class Theme():
    @classmethod
    def load(cls):
        defaults_path = files("lute").joinpath("defaults.jsonc")
        defaults = load_jsonc(defaults_path)

        user_defaults_path = config.lute_dir / "user_defaults.jsonc"
        user_defaults = load_jsonc(user_defaults_path)

        selected_theme_path = config.themes_dir / f"{config.selected_theme}.jsonc"
        selected_theme = load_jsonc_validate(selected_theme_path)

        user_overrides_path = config.themes_dir / "user_overrides.jsonc"
        user_overrides = load_jsonc(user_overrides_path)


)
        
        # load each layer DONE → normalize each layer → deep-merge in order → resolve references → create Theme
        
