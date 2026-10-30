import lute.config as config
from dataclasses import *

class Theme():
    name: str
    description: str
    authors: list
    version: str
    lute_version: str
    variant: str
    darkest: str
    darker: str
    lighter: str
    lightest: str

    colors: dict

    @classmethod
    def from_dict(cls, data: dict) -> "Theme":
        metadata = data["metadata"]

        return cls(
            name = metadata["name"]
            description = metadata["description"]
            author = metadata["author"]
            version = metadata["version"]
            lute_version = metadata["lute_version"]
            variant = metadata["variant"]
            darkest = metadata["darkest"]
            darker = metadata["darker"]
            lighter = metadata["lighter"]
            lightest = metadata["lightest"]
            colors = data["colors"]
                )

