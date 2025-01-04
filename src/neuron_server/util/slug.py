import re
from uuid import uuid4


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9-_]", "", text)[:255].lower().replace(" ", "-")


def safe_filename(
    prefix: str,
    suffix: str,
    extension: str,
) -> str:
    return f"{slugify(prefix)}_{uuid4().hex[:8]}_{slugify(suffix)}.{extension}".lower()
