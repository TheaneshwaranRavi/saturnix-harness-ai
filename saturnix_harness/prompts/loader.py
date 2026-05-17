from __future__ import annotations

from functools import lru_cache
from importlib import resources


@lru_cache
def load_prompt(name: str) -> str:
    """Load a packaged prompt template by filename."""

    if "/" in name or "\\" in name:
        raise ValueError("Prompt names must be simple filenames.")
    prompt_path = resources.files("saturnix_harness.prompts").joinpath(name)
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt template not found: {name}")
    return prompt_path.read_text(encoding="utf-8").strip()

