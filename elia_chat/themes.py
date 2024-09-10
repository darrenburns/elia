from pydantic import BaseModel, Field
import yaml

from elia_chat.locations import theme_directory


class Theme(BaseModel):
    name: str = Field(exclude=True)
    primary: str
    secondary: str | None = None
    background: str | None = None
    surface: str | None = None
    panel: str | None = None
    warning: str | None = None
    error: str | None = None
    success: str | None = None
    accent: str | None = None
    dark: bool = True


def load_user_themes() -> dict[str, Theme]:
    """Load user themes from "~/.config/elia/themes".

    Returns:
        A dictionary mapping theme names to theme objects.
    """
    themes: dict[str, Theme] = {}
    for path in theme_directory().iterdir():
        path_suffix = path.suffix
        if path_suffix == ".yaml" or path_suffix == ".yml":
            with path.open() as theme_file:
                theme_content = yaml.load(theme_file, Loader=yaml.FullLoader) or {}
                try:
                    themes[theme_content["name"]] = Theme(**theme_content)
                except KeyError:
                    raise ValueError(
                        f"Invalid theme file {path}. A `name` is required."
                    )
    return themes
