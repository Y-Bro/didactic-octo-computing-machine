import csv


def read_template(path: str) -> dict:
    """
    Returns {"columns": list[str], "sample_rows": list[dict]}
    Raises FileNotFoundError if path does not exist.
    Raises ValueError if file is empty.
    """
    with open(path, newline="", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        raise ValueError("Template CSV is empty.")

    reader = csv.DictReader(content.splitlines())
    columns = reader.fieldnames
    sample_rows = [row for row in reader]

    return {"columns": list(columns), "sample_rows": sample_rows}
