from typing import TypedDict, List
import re


class SpokenLine(TypedDict):
    voice: str
    text: str


def parse_script(script: str, remove_actions: bool = False) -> List[SpokenLine]:
    """
    Parses a script string and returns a list of dictionaries with 'voice' and 'text' keys.

    The script format should be:
    [Voice]
    Line of text *action* more text

    [Another Voice]
    Another line of text

    Args:
        script (str): The script string to parse.
        remove_actions (bool): If True, removes text between asterisks. Defaults to False.

    Returns:
        List[SpokenLine]: A list of dictionaries containing 'voice' and 'text' keys.
    """
    lines = script.strip().split("\n")
    parsed_lines = []
    current_voice = None
    current_text = []

    for line in lines:
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            if current_voice and current_text:
                text = "\n".join(current_text)
                if remove_actions:
                    text = re.sub(r"\*[^*]+\*", "", text)
                parsed_lines.append({"voice": current_voice, "text": text})
            current_voice = line[1:-1]
            current_text = []
        elif current_voice and len(line.strip()) > 0:
            current_text.append(line)

    if current_voice and current_text:
        text = "\n".join(current_text)
        if remove_actions:
            text = re.sub(r"\*[^*]+\*", "", text)
        parsed_lines.append({"voice": current_voice, "text": text})

    return parsed_lines
