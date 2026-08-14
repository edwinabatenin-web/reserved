"""Small dependency-free security helpers shared by web delivery code."""


def spreadsheet_safe(value):
    """Prevent user-controlled CSV cells from executing as formulae."""
    if not isinstance(value, str):
        return value
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def spreadsheet_safe_row(row):
    return {key: spreadsheet_safe(value) for key, value in row.items()}
