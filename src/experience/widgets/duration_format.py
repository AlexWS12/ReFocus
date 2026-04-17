def format_focus_duration(seconds: float | int) -> str:
    """Format focus duration using seconds, minutes, or hours based on size."""
    total_seconds = float(seconds or 0)
    if total_seconds < 0:
        total_seconds = 0.0

    if total_seconds < 60:
        value = round(total_seconds)
        unit = "second" if value == 1 else "seconds"
        return f"{value} {unit}"

    if total_seconds < 3600:
        minutes = total_seconds / 60.0
        rounded = round(minutes, 1 if minutes < 10 else 0)
        rounded = int(rounded) if float(rounded).is_integer() else rounded
        unit = "minute" if rounded == 1 else "minutes"
        return f"{rounded} {unit}"

    hours = total_seconds / 3600.0
    rounded = round(hours, 1 if hours < 10 else 0)
    rounded = int(rounded) if float(rounded).is_integer() else rounded
    unit = "hour" if rounded == 1 else "hours"
    return f"{rounded} {unit}"