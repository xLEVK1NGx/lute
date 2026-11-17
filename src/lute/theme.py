import colorsys
from copy import deepcopy
from dataclasses import *
from enum import Enum
from importlib.resources import files, as_file
import json5 as json
from jsonschema import validate, Draft202012Validator
from lute.config import *
from pathlib import Path
import re
from rich import print
import subprocess

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
            case "font_sizes":
                value = normalize_font_sizes(value)

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
            value[field] = recursive_normalization(value[field],
                                                   field_schema["properties"][field],
                                                   schema)
    elif isinstance(value, list):
        for index in range(len(value)): 
            value[index] = recursive_normalization(value[index], field_schema["items"], schema)

    return value

class GenerateTone(Enum):
    DARK = "dark"
    LIGHT = "light"

def normalize_color_variants(value):
    if isinstance(value, str):
        if not value.startswith("#"):
            return value
        return {"light": GenerateTone.LIGHT, "base": value, "dark": GenerateTone.DARK}
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

def normalize_font_sizes(fonts: dict) -> dict:
    if "sizes" not in fonts:
        return fonts

    for slot_name in ("normal", "serif", "monospace", "title", "small"):
        if slot_name in fonts:
            fonts[slot_name].setdefault("sizes", fonts["sizes"].copy())

    return fonts

# fonts validation
def validate_fonts(data: dict):
    config = Config.load()
    if "fonts" not in data:
        return
    shell_result = subprocess.run("fc-list | awk -F ': '  '{print $2}' | awk -F ':' '{print $1}'",
                                  shell=True,
                                  capture_output=True,
                                  text=True,
                                  check=True)
    fc_listed_fonts = shell_result.stdout.split("\n")
    conf_used_fonts = [(name, font) for name, font in data["fonts"].items() if name != "sizes"]
    for name, font in conf_used_fonts:
        if font["family"] in fc_listed_fonts:
            if config.verbose:
                print(f"Font {font['family']} found!")
            continue
        else:
            print(f"[bold red]Font {font['family']} not found! Not gonna load it...")
            del data["fonts"][name]

# merging layers and resolving color references

@dataclass
class ColorReference():
    color_reference: str
    def resolve(self, theme_dict: dict): # returns the actual theme of that reference
        steps = self.color_reference.split(".")
        path = theme_dict
        for step in steps:
            path = path[step]
        return path

@dataclass
class ColorReferenceWithPartOverride():
    base: ColorReference    # base color reference e.g. border = "palette.red"
    overrides: dict         # dict of overrides for the specific field, e.g. border = {"light": "#ff9999"}

def convert_strs_to_color_refs(data: dict) -> dict: # func written by AI
    """Return a copy of data with color-reference strings wrapped."""
    reference_pattern = re.compile(
        r"(?:palette|UI|semantic|terminal)(?:\.[A-Za-z0-9_]+)+"
    )
    def convert(value):
        if isinstance(value, dict):
            return {
                key: convert(child)
                for key, child in value.items()
            }
        if isinstance(value, list):
            return [convert(item) for item in value]
        if isinstance(value, str) and reference_pattern.fullmatch(value):
            return ColorReference(value)
        return value
    return convert(data)

def deep_merge(base: dict, overrides_dict: dict):
    final = deepcopy(base)
    overrides = deepcopy(overrides_dict)
    for field in overrides:
        if field not in base:
            final[field] = overrides[field]
        else:
            if isinstance(base[field], dict) and isinstance(overrides[field], dict):
                final[field] = deep_merge(base[field], overrides[field])
            elif (
                    isinstance(base[field], (ColorReference, ColorReferenceWithPartOverride))
                    and isinstance(overrides[field], dict)
                    and {"base", "dark", "light"} <= overrides[field].keys()
                ):    
                # A complete color replaces the earlier reference.
                final[field] = overrides[field]
            elif isinstance(base[field], ColorReference) and isinstance(overrides[field], dict):
                final[field] = ColorReferenceWithPartOverride(base[field], overrides[field])
            elif isinstance(base[field], ColorReferenceWithPartOverride) and isinstance(overrides[field], dict):
                final[field] = ColorReferenceWithPartOverride(
                        base[field].base,
                        deep_merge(base[field].overrides, overrides[field])
                        )
            else:
                final[field] = overrides[field]
    return final

def resolve_color_references(theme: dict, schema: dict) -> dict:  # func written by AI
    """
    Resolve color references and generate missing color variants.

    Reference paths are relative to theme["colors"].
    Returns a new dictionary.
    """

    colors = theme["colors"]
    colors_schema = schema["properties"]["colors"]

    def follow_schema_refs(field_schema):
        """Follow local schema references."""
        while "$ref" in field_schema:
            field_schema = resolve(field_schema["$ref"], schema)
        return field_schema

    def is_color_variants(field_schema):
        field_schema = follow_schema_refs(field_schema)
        return field_schema.get("x-lute-normalize") == "color_variants"

    def object_schema(field_schema):
        """Find the schema containing an object's properties."""
        field_schema = follow_schema_refs(field_schema)

        if "oneOf" in field_schema:
            for branch in field_schema["oneOf"]:
                branch = follow_schema_refs(branch)

                if branch.get("type") == "object":
                    return branch

            raise ValueError("No object branch found in schema")

        return field_schema

    def child_schema(field_schema, key):
        field_schema = object_schema(field_schema)
        return field_schema["properties"][key]

    def resolve_reference(reference, active):
        path = reference.color_reference

        if path in active:
            chain = " -> ".join((*active, path))
            raise ValueError(f"Circular color reference: {chain}")

        active = (*active, path)
        current = colors
        current_schema = colors_schema
        parent = None
        parent_schema = None

        for step in path.split("."):
            if (
                isinstance(current, ColorReferenceWithPartOverride)
                and step in current.overrides
                and not isinstance(current.overrides[step], (dict, GenerateTone))
            ):
                parent = current.overrides
                parent_schema = current_schema
                current = current.overrides[step]
                current_schema = child_schema(current_schema, step)
                continue
            # A reference may appear in the middle of another path.
            if isinstance(
                current,
                (ColorReference, ColorReferenceWithPartOverride),
            ):
                current = resolve_value(
                    current,
                    current_schema,
                    active,
                    parent,
                    parent_schema,
                )

            if not isinstance(current, dict):
                raise ValueError(
                    f"Cannot follow {path!r}: "
                    f"the value before {step!r} is not an object"
                )

            # A missing dark/light variant can be generated on demand.
            if step not in current:
                if (
                    is_color_variants(current_schema)
                    and step in ("dark", "light")
                    and "base" in current
                ):
                    base_schema = child_schema(current_schema, "base")
                    base = resolve_value(
                        current["base"],
                        base_schema,
                        active,
                        current,
                        current_schema,
                    )

                    adjustment = -0.1 if step == "dark" else 0.1
                    return generate_tone(base, adjustment)

                raise ValueError(
                    f"Color reference {path!r} has no field {step!r}"
                )

            parent = current
            parent_schema = current_schema
            current = current[step]
            current_schema = child_schema(current_schema, step)

        return resolve_value(
            current,
            current_schema,
            active,
            parent,
            parent_schema,
        )

    def resolve_value(
        value,
        field_schema,
        active,
        parent=None,
        parent_schema=None,
    ):
        # A tone marker needs the final base of its parent color.
        if isinstance(value, GenerateTone):
            if parent is None or "base" not in parent:
                raise ValueError("Cannot generate a tone without a base color")

            base_schema = child_schema(parent_schema, "base")
            base = resolve_value(
                parent["base"],
                base_schema,
                active,
                parent,
                parent_schema,
            )

            adjustment = -0.1 if value is GenerateTone.DARK else 0.1
            return generate_tone(base, adjustment)

        if isinstance(value, ColorReference):
            resolved = resolve_reference(value, active)

            # A single-color reference used in a variant field becomes
            # a color object whose dark and light tones are generated.
            if is_color_variants(field_schema) and isinstance(resolved, str):
                resolved = {
                    "base": resolved,
                    "dark": GenerateTone.DARK,
                    "light": GenerateTone.LIGHT,
                }

                return resolve_value(resolved, field_schema, active)

            return resolved

        if isinstance(value, ColorReferenceWithPartOverride):
            base = resolve_reference(value.base, active)

            if not isinstance(base, dict):
                raise ValueError(
                    f"Cannot apply partial overrides to "
                    f"{value.base.color_reference!r}: "
                    f"it did not resolve to an object"
                )

            combined = deep_merge(base, value.overrides)
            return resolve_value(combined, field_schema, active)

        if isinstance(value, dict):
            result = {}

            for key, child in value.items():
                result[key] = resolve_value(
                    child,
                    child_schema(field_schema, key),
                    active,
                    value,
                    field_schema,
                )

            # Finalize variants that remain absent after merging.
            if is_color_variants(field_schema):
                if "base" not in result:
                    raise ValueError(
                        "Cannot finalize a color without a base value"
                    )

                if "dark" not in result:
                    result["dark"] = generate_tone(result["base"], -0.1)

                if "light" not in result:
                    result["light"] = generate_tone(result["base"], 0.1)

            return result

        if isinstance(value, list):
            field_schema = follow_schema_refs(field_schema)
            item_schema = field_schema.get("items")

            if item_schema is None and "oneOf" in field_schema:
                for branch in field_schema["oneOf"]:
                    branch = follow_schema_refs(branch)

                    if branch.get("type") == "array":
                        item_schema = branch.get("items")
                        break

            if item_schema is None:
                raise ValueError("No item schema found for list")

            return [
                resolve_value(item, item_schema, active)
                for item in value
            ]

        return value

    return resolve_value(theme, schema, ())

# finally, some more color shit.

def generate_tone(color: str, adjustment: float) -> str: # func made by ai cos im lazy
    """Adjust a hex color's HSV value; preserve alpha if present."""

    hex_digits = color.removeprefix("#")

    # Expand #RGB and #RGBA into #RRGGBB and #RRGGBBAA.
    if len(hex_digits) in (3, 4):
        hex_digits = "".join(char * 2 for char in hex_digits)

    rgb = hex_digits[:6]
    alpha = hex_digits[6:]  # Empty if there is no alpha.

    red = int(rgb[0:2], 16) / 255
    green = int(rgb[2:4], 16) / 255
    blue = int(rgb[4:6], 16) / 255

    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)

    value = max(0.0, min(1.0, value + adjustment))

    red, green, blue = colorsys.hsv_to_rgb(hue, saturation, value)

    return (
        f"#{round(red * 255):02x}"
        f"{round(green * 255):02x}"
        f"{round(blue * 255):02x}"
        f"{alpha}"
    )


class ThemeNode:
    def __init__(self, data: dict):
        for key, value in data.items():
            setattr(self, key, self.convert(value))

    @classmethod
    def convert(cls, value):
        if isinstance(value, dict):
            return ThemeNode(value)

        if isinstance(value, list):
            return [cls.convert(item) for item in value]

        return value

class Theme(ThemeNode):
    @classmethod
    def load_full(cls) -> "Theme":
        config = Config.load()
        with as_file(files("lute").joinpath("theme.schema.json")) as file:
            schema = load_jsonc(file)

            defaults_path = files("lute").joinpath("defaults.jsonc")
            defaults = load_jsonc_noreq(defaults_path)
            recursive_normalization(defaults, schema, schema)
            defaults = convert_strs_to_color_refs(defaults)

            user_defaults_path = config.lute_dir / "user-defaults.jsonc"
            user_defaults = {}
            if user_defaults_path.exists():
                user_defaults = load_jsonc_noreq(user_defaults_path)
                validate_fonts(user_defaults)
                recursive_normalization(user_defaults, schema, schema)
                user_defaults = convert_strs_to_color_refs(user_defaults)

            selected_theme_path = config.themes_dir / f"{config.selected_theme}.jsonc"
            selected_theme = load_jsonc_req(selected_theme_path)
            validate_fonts(selected_theme)
            recursive_normalization(selected_theme, schema, schema)
            selected_theme = convert_strs_to_color_refs(selected_theme)

            user_overrides_path = config.lute_dir / "user-overrides.jsonc"
            user_overrides = {}
            if user_overrides_path.exists():
                user_overrides = load_jsonc_noreq(user_overrides_path)
                validate_fonts(user_overrides)
                recursive_normalization(user_overrides, schema, schema)
                user_overrides = convert_strs_to_color_refs(user_overrides)

            final_dict = deep_merge(defaults, user_defaults)
            final_dict = deep_merge(final_dict, selected_theme)
            final_dict = deep_merge(final_dict, user_overrides)

            final_dict = resolve_color_references(final_dict, schema)

            return cls(final_dict)
    
    @classmethod
    def load_file(cls) -> "Theme":
        config = Config.load()
        with as_file(files("lute").joinpath("theme.schema.json")) as file:
            schema = load_jsonc(file)

            selected_theme_path = config.themes_dir / f"{config.selected_theme}.jsonc"
            selected_theme = load_jsonc_req(selected_theme_path)
            validate_fonts(selected_theme)
            recursive_normalization(selected_theme, schema, schema)
            selected_theme = convert_strs_to_color_refs(selected_theme)

            final_dict = resolve_color_references(selected_theme, schema)

            return cls(final_dict)

