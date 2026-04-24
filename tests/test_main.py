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



def test_build_provider_uses_explicit_model_over_env_var():
    with patch("agent.providers.gemini.genai"):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake", "GEMINI_MODEL": "from-env"}, clear=True):
            provider = build_provider("gemini", model="from-flag")
    assert provider._model_name == "from-flag"


def test_build_provider_uses_gemini_env_var_when_no_model_arg():
    with patch("agent.providers.gemini.genai"):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake", "GEMINI_MODEL": "env-value"}, clear=True):
            provider = build_provider("gemini")
    assert provider._model_name == "env-value"


def test_build_provider_uses_anthropic_env_var_when_no_model_arg():
    with patch("agent.providers.claude.anthropic.Anthropic"):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake", "ANTHROPIC_MODEL": "env-value"}, clear=True):
            provider = build_provider("claude")
    assert provider._model == "env-value"


def test_build_provider_falls_back_to_provider_default():
    with patch("agent.providers.gemini.genai"):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}, clear=True):
            gemini_provider = build_provider("gemini")
    with patch("agent.providers.claude.anthropic.Anthropic"):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake"}, clear=True):
            claude_provider = build_provider("claude")
    assert gemini_provider._model_name == "gemini-2.0-flash"
    assert claude_provider._model == "claude-sonnet-4-6"


def test_model_cli_flag_parses():
    from main import build_arg_parser
    args = build_arg_parser().parse_args(["--sow", "x", "--template", "y", "--model", "foo-1"])
    assert args.model == "foo-1"
    args_no_flag = build_arg_parser().parse_args(["--sow", "x", "--template", "y"])
    assert args_no_flag.model is None


def test_load_dotenv_populates_env_from_dotenv_file(tmp_path, monkeypatch):
    """main.load_dotenv pushes .env keys into os.environ."""
    import os
    from main import load_dotenv

    env_path = tmp_path / ".env"
    env_path.write_text("_DOTENV_TEST_SIGIL=loaded-from-dotenv\n")
    monkeypatch.delenv("_DOTENV_TEST_SIGIL", raising=False)

    load_dotenv(dotenv_path=env_path)

    assert os.environ.get("_DOTENV_TEST_SIGIL") == "loaded-from-dotenv"

