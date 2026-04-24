from agent.prompt import build_system_prompt


def test_prompt_includes_grounding_rule():
    prompt = build_system_prompt(columns=["Phase", "Milestone", "Deliverable"])
    assert "source_quote" in prompt


def test_prompt_includes_developer_profile():
    prompt = build_system_prompt(columns=["Phase"])
    assert "senior developer" in prompt.lower()
    assert "3 years" in prompt.lower()


def test_prompt_includes_flag_gap_instruction():
    prompt = build_system_prompt(columns=["Phase"])
    assert "flag_gap" in prompt


def test_prompt_includes_column_names():
    prompt = build_system_prompt(columns=["Phase", "Deliverable", "Start Date"])
    assert "Phase" in prompt
    assert "Deliverable" in prompt
    assert "Start Date" in prompt
