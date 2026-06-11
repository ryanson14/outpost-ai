import os
from pathlib import Path

import yaml

from security import MAX_PROFILE_CHARS, strip_control_chars, truncate

DEFAULT_PROFILE_PATH = Path(__file__).parent / "profile.yaml"
REQUIRED_FIELDS = ("product_name", "product_description", "q3_goal", "roadmap_focus")


def _format_profile(data: dict[str, str]) -> str:
    return (
        f"Product Name: {data['product_name']} ({data['product_description']})\n"
        f"Current Q3 Goal: {data['q3_goal']}\n"
        f"Current Roadmap Focus: {data['roadmap_focus']}"
    )


def load_user_profile(path: Path | str | None = None) -> str:
    """Load and format the PM product profile from profile.yaml."""
    profile_path = Path(
        path or os.environ.get("OUTPOST_PROFILE_PATH", DEFAULT_PROFILE_PATH)
    )

    if not profile_path.is_file():
        raise FileNotFoundError(
            f"Profile not found: {profile_path}. "
            "Create profile.yaml or set OUTPOST_PROFILE_PATH."
        )

    with profile_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid profile format in {profile_path}: expected a YAML mapping.")

    missing = [field for field in REQUIRED_FIELDS if not data.get(field)]
    if missing:
        raise ValueError(f"Profile missing required fields: {', '.join(missing)}")

    cleaned = {
        field: strip_control_chars(str(data[field]).strip())
        for field in REQUIRED_FIELDS
    }
    return truncate(_format_profile(cleaned), MAX_PROFILE_CHARS, label="user profile")
