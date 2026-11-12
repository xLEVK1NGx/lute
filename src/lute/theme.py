from lute.config import *
from importlib.resources import files, as_file
from dataclasses import *
from jsonschema import validate, Draft202012Validator
import json5 as json

config = Config.load()

# functions to load jsonc files and such

def load_jsonc(path) -> dict:
    """ Returns a dict with all the data from the specified jsonc file """
    with path.open(encoding="UTF-8") as file:
        return json.load(file)

def remove_requireds(data: dict):
    """ Helper func to remove all "required" fields from a json schema """
    if isinstance(data, dict):
        data.pop("required", None)
        for value in data.values():
            remove_requireds(value)
    elif isinstance(data, list):
        for item in data: 
            remove_requireds(item)

def load_jsonc_req(path: Path) -> dict:
    """ Load a jsonc file and check for presence of required fields """
    with as_file(files("lute").joinpath("theme.schema.json")) as file:
        schema = load_jsonc(file) 
    Draft202012Validator.check_schema(schema)
    theme_data = load_jsonc(path)

    validate(instance=theme_data, schema=schema)
    return theme_data

def load_jsonc_noreq(path) -> dict:
    """ Load a jsonc file and DO NOT check for presence of required fields """
    with as_file(files("lute").joinpath("theme.schema.json")) as file:
        schema = load_jsonc(file) 
    Draft202012Validator.check_schema(schema)
    theme_data = load_jsonc(path)
    remove_requireds(schema)
    validate(instance=theme_data, schema=schema)
    return theme_data

# normalizing functions

def resolve(ref: str, schema) -> dict: # this function was made by AI
    """ Resolve a json "$ref" to the definition it points at """
    if not ref.startswith("#/"):
        raise ValueError(f"Unsupported schema reference: {ref}")
    result = schema
    for part in ref[2:].split("/"):
        # JSON Pointer escaping:
        # ~1 means "/" and ~0 means "~".
        part = part.replace("~1", "/").replace("~0", "~")
        result = result[part]
    return result

def matches_type(value, schema_type: str) -> bool: # this function was made by AI
    """Check whether a Python value matches a JSON Schema type."""
    match schema_type:
        case "object":
            return isinstance(value, dict)
        case "array":
            return isinstance(value, list)
        case "string":
            return isinstance(value, str)
        case "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        case "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        case "boolean":
            return isinstance(value, bool)
    return False

def recursive_normalization(value, field_schema, schema):
    if "$ref" in field_schema:
        resolved_schema = resolve(field_schema["$ref"], schema)
        return recursive_normalization(value, resolved_schema, schema)

    if "x-lute-normalize" in field_schema:
        match field_schema["x-lute-normalize"]:
            case "color_variants":
                value = normalize_color_variants(value)
            case "corner_radius":
                value = normalize_corner_radius(value)
            case "gaps":
                value = normalize_gaps(value)
            case "side_values":
                value = normalize_side_values(value)
            case "spacing_scale":
                value = normalize_spacing_scale(value)

    if "oneOf" in field_schema:
        for branch in field_schema["oneOf"]:
            if "$ref" in branch:
                branch = resolve(branch["$ref"], schema)
            if matches_type(value, branch.get("type")):
                field_schema = branch
                break
        else: 
            raise ValueError(f"No oneOf branch matches value {value!r}")

    if isinstance(value, dict):
        for field in value:
            value[field] = recursive_normalization(value[field], field_schema["properties"][field], schema)
    elif isinstance(value, list):
        for index in range(len(value)): 
            value[index] = recursive_normalization(value[index], field_schema["items"], schema)

    return value

def normalize_color_variants(value):
    if isinstance(value, str):
        if not value.startswith("#"):
            return value
        return {"light": value, "base": value, "dark": value}
    return value

def normalize_corner_radius(value):
    if isinstance(value, int) and not isinstance(value, bool):
        return [value, value, value, value]
    return value

def normalize_gaps(value):
    if isinstance(value, int): 
        return {"inner": value, "outer": value}
    return value

def normalize_side_values(value):
    if isinstance(value, int):
        return [value, value, value, value]
    elif isinstance(value, list):
        match len(value):
            case 1:
                return [value[0], value[0], value[0], value[0]]
            case 2: 
                return [value[0], value[1], value[0], value[1]]
            case 3:
                return [value[0], value[1], value[2], value[1]]
            case 4:
                return value
    return value

def normalize_spacing_scale(value):
    if isinstance(value, int):
        return {"sm": value, "md": value, "lg": value}
    return value

# merging layers

@dataclass
class ColorReferenceWithPartOverride():
    base: ColorReference# base color reference e.g. border = "palette.red"
    overrides: dict     # dict of overrides for the specific field, e.g. border = {"light": "#ff9999"}

@dataclass
class ColorReference():
    color_reference: str
    steps: list
    def resolve(self, schema: dict): # returns the actual theme of that reference
        def create_steps(ref: str):
            # sep str into steps (1.2.3.4...)
            temp_steps = []
            tmp = ""
            for l in ref:
                if l == ".":
                    temp_steps.append(tmp)
                    tmp = ""
                else:
                    tmp.join(l)
            temp_steps.append(tmp) # last word in a reference doesn't have a "." so we add it manually
            return temp_steps

        steps = create_steps(self.color_reference)
        path = self
        for i in range(len(steps)):
            path = self[steps[i]]
        return path

def resolve_color_references(data: dict):
    return
    for el in data:
        if isinstance(el, dict): 
            resolve_color_references(el)
        elif isinstance(el, ColorReference):
            el = el.resolve(schema)

def deep_merge(base: dict, overrides: dict):
    for field in base:
        if field in overrides:
            if isinstance(base[field], dict) and isinstance(overrides[field], dict):
                deep_merge(base[field], overrides[field])
            elif isinstance(base[field], ColorReference) and isinstance(overrides[field], dict):
                ColorReferenceWithPartOverride(base[field], overrides[field])
            else:
                base[field] = overrides[field]

@dataclass
class Theme():
    @classmethod
    def load(cls) -> "Theme":
        with as_file(files("lute").joinpath("theme.schema.json")) as file:
            schema = load_jsonc(file)

            defaults_path = files("lute").joinpath("defaults.jsonc")
            defaults = load_jsonc_noreq(defaults_path)
            recursive_normalization(defaults, schema, schema)

            user_defaults_path = config.lute_dir / "user_defaults.jsonc"
            user_defaults = {}
            if user_defaults_path.exists():
                user_defaults = load_jsonc_noreq(user_defaults_path)
                recursive_normalization(user_defaults, schema, schema)

            selected_theme_path = config.themes_dir / f"{config.selected_theme}.jsonc"
            selected_theme = load_jsonc_req(selected_theme_path)
            recursive_normalization(selected_theme, schema, schema)

            user_overrides_path = config.lute_dir / "user_overrides.jsonc"
            user_overrides = {}
            if user_overrides_path.exists():
                user_overrides = load_jsonc_noreq(user_overrides_path)
                recursive_normalization(user_overrides, schema, schema)

            return cls()

        # load each layer DONE → normalize each layer DONE → deep-merge in order → resolve references → create Theme

