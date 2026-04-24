import pytest
from template.reader import read_template


def test_read_template_returns_columns(tmp_path):
    csv_file = tmp_path / "template.csv"
    csv_file.write_text("Phase,Milestone,Deliverable,Start Date,End Date,Estimated Days,Notes\n")
    result = read_template(str(csv_file))
    assert result["columns"] == ["Phase", "Milestone", "Deliverable", "Start Date", "End Date", "Estimated Days", "Notes"]


def test_read_template_returns_sample_rows(tmp_path):
    csv_file = tmp_path / "template.csv"
    csv_file.write_text(
        "Phase,Milestone,Deliverable\n"
        "Planning,Kickoff,Kickoff Meeting\n"
    )
    result = read_template(str(csv_file))
    assert len(result["sample_rows"]) == 1
    assert result["sample_rows"][0]["Phase"] == "Planning"


def test_read_template_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        read_template("/nonexistent/path/template.csv")


def test_read_template_raises_on_empty_file(tmp_path):
    csv_file = tmp_path / "template.csv"
    csv_file.write_text("")
    with pytest.raises(ValueError, match="Template CSV is empty"):
        read_template(str(csv_file))
