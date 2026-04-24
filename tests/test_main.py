import pytest
from unittest.mock import patch, MagicMock
from main import build_provider, load_sow


def test_build_provider_returns_gemini_by_default():
    from agent.providers.gemini import GeminiProvider
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}):
        provider = build_provider("gemini")
    assert isinstance(provider, GeminiProvider)


def test_build_provider_returns_claude():
    from agent.providers.claude import ClaudeProvider
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}):
        provider = build_provider("claude")
    assert isinstance(provider, ClaudeProvider)


def test_build_provider_raises_on_missing_gemini_key():
    with patch.dict("os.environ", {}, clear=True):
        import os
        os.environ.pop("GEMINI_API_KEY", None)
        with pytest.raises(EnvironmentError, match="GEMINI_API_KEY"):
            build_provider("gemini")


def test_build_provider_raises_on_missing_claude_key():
    with patch.dict("os.environ", {}, clear=True):
        import os
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
            build_provider("claude")


def test_load_sow_dispatches_pdf(tmp_path):
    pdf_path = tmp_path / "sow.pdf"
    pdf_path.write_bytes(b"fake")
    with patch("main.parse_pdf") as mock_pdf:
        mock_pdf.return_value = {"text": "hello", "images": []}
        result = load_sow(str(pdf_path))
    mock_pdf.assert_called_once()
    assert result["text"] == "hello"


def test_load_sow_dispatches_docx(tmp_path):
    docx_path = tmp_path / "sow.docx"
    docx_path.write_bytes(b"fake")
    with patch("main.parse_docx") as mock_docx:
        mock_docx.return_value = {"text": "hello", "images": []}
        result = load_sow(str(docx_path))
    mock_docx.assert_called_once()


def test_load_sow_raises_on_unsupported_format(tmp_path):
    txt_path = tmp_path / "sow.txt"
    txt_path.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported file format"):
        load_sow(str(txt_path))


def test_credentials_defaults_to_env_var():
    from main import build_arg_parser
    with patch.dict("os.environ", {"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/svc.json"}):
        args = build_arg_parser().parse_args(["--sow", "x.pdf", "--template", "t.csv"])
    assert args.credentials == "/path/to/svc.json"


def test_credentials_cli_flag_overrides_env_var():
    from main import build_arg_parser
    with patch.dict("os.environ", {"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/svc.json"}):
        args = build_arg_parser().parse_args(["--sow", "x.pdf", "--template", "t.csv", "--credentials", "override.json"])
    assert args.credentials == "override.json"


def test_credentials_defaults_to_credentials_json_when_env_var_unset():
    import os
    from main import build_arg_parser
    with patch.dict("os.environ", {}, clear=True):
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        args = build_arg_parser().parse_args(["--sow", "x.pdf", "--template", "t.csv"])
    assert args.credentials == "credentials.json"
