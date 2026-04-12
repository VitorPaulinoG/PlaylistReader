def parse_duration_seconds(value: str) -> int | None:
    if not value or ":" not in value:
        return None
    parts = value.split(":")
    if not all(part.isdigit() for part in parts):
        return None
    total = 0
    for part in parts:
        total = (total * 60) + int(part)
    return total