import argparse
import logging
import os
import time

from parsers.pdf import parse_pdf
from parsers.docx import parse_docx
from template.reader import read_template
from agent.loop import run_agent
from sheets.writer import SheetsWriter


def build_provider(llm: str, model: str | None = None):
    if llm == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY environment variable is not set.")
        resolved_model = model or os.environ.get("GEMINI_MODEL")
        from agent.providers.gemini import GeminiProvider
        if resolved_model:
            return GeminiProvider(api_key=api_key, model=resolved_model)
        return GeminiProvider(api_key=api_key)
    elif llm == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")
        resolved_model = model or os.environ.get("ANTHROPIC_MODEL")
        from agent.providers.claude import ClaudeProvider
        if resolved_model:
            return ClaudeProvider(api_key=api_key, model=resolved_model)
        return ClaudeProvider(api_key=api_key)
    else:
        raise ValueError(f"Unknown LLM provider: {llm}. Choose 'gemini' or 'claude'.")


def load_sow(path: str) -> dict:
    with open(path, "rb") as f:
        data = f.read()
    if path.lower().endswith(".pdf"):
        return parse_pdf(data)
    elif path.lower().endswith(".docx"):
        return parse_docx(data)
    else:
        raise ValueError(f"Unsupported file format: {path}. Use .pdf or .docx.")


def build_arg_parser():
    parser = argparse.ArgumentParser(description="SoW Project Planner Agent")
    parser.add_argument("--sow", required=True, help="Path to SoW file (.pdf or .docx)")
    parser.add_argument("--template", required=True, help="Path to template CSV file")
    parser.add_argument("--llm", default="gemini", choices=["gemini", "claude"], help="LLM provider (default: gemini)")
    parser.add_argument("--model", default=None, help="Override default LLM model (else uses $GEMINI_MODEL / $ANTHROPIC_MODEL if set, else provider default).")
    parser.add_argument("--title", default="Project Plan", help="Title for the output Google Sheet")
    parser.add_argument("--verbose", action="store_true", default=False, help="Enable DEBUG-level logging")
    return parser


def main():
    args = build_arg_parser().parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    print(f"Loading SoW from {args.sow}...")
    sow_data = load_sow(args.sow)
    print(f"Extracted {len(sow_data['text'])} characters of text and {len(sow_data['images'])} images.")

    print(f"Loading template from {args.template}...")
    template = read_template(args.template)
    print(f"Template columns: {', '.join(template['columns'])}")

    print(f"Initializing {args.llm} provider...")
    provider = build_provider(args.llm, model=args.model)

    sheets_writer = SheetsWriter()

    print("Running agent...")
    start = time.monotonic()
    result = run_agent(
        sow_data=sow_data,
        template=template,
        provider=provider,
        sheets_writer=sheets_writer,
    )
    elapsed = time.monotonic() - start

    print()
    print("=" * 50)
    print("Run Summary")
    print("=" * 50)
    print(f"Model:      {args.llm}")
    print(f"Iterations: {result.iterations}")
    print(f"Rows:       {result.rows}")
    print(f"Gaps:       {result.gaps}")
    print(f"Elapsed:    {elapsed:.1f}s")
    print(f"Sheet:      {result.sheet_url}")


if __name__ == "__main__":
    main()
