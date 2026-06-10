import re


def sanitize_filename(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-zA-Z0-9а-яА-Я._-]+", "_", value)
    return value.strip("_")