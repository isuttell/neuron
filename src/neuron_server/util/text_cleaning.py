import re


def clean_action_text(text: str) -> str:
    """Remove text enclosed in asterisks including the asterisks themselves."""
    return re.sub(r"\*[^*]+\*", " ", text).strip()
