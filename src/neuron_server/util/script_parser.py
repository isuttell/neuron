import re
from typing import TypedDict


class SpokenLine(TypedDict):
    voice: str
    text: str


def parse_script(script: str, remove_actions: bool = False) -> list[SpokenLine]:
    """Parse a script string into a list of voice and text entries.

    The script format should be:
    [Voice]
    Line of text *action* more text

    [Another Voice]
    Another line of text

    Args:
        script: The script string to parse
        remove_actions: If True, removes text between asterisks

    Returns:
        A list of dictionaries containing 'voice' and 'text' keys
    """
    lines = script.strip().split("\n")
    parsed_lines: list[SpokenLine] = []
    current_voice = None
    current_text: list[str] = []

    def add_current_line() -> None:
        if current_voice and current_text:
            text = "\n".join(current_text)
            if remove_actions:
                text = re.sub(r"\*[^*]+\*", "", text)
            parsed_lines.append({"voice": current_voice, "text": text})

    for raw_line in lines:
        stripped_line = raw_line.strip()
        if stripped_line.startswith("[") and stripped_line.endswith("]"):
            add_current_line()
            current_voice = stripped_line[1:-1]
            current_text = []
        elif current_voice and len(stripped_line) > 0:
            current_text.append(stripped_line)

    add_current_line()
    return parsed_lines
