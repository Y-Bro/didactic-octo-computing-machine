import logging
import time
from dataclasses import dataclass

from agent.prompt import build_system_prompt
from agent.tools import get_tool_schemas, ToolExecutor
from agent.providers.base import LLMProvider, ToolResult

MAX_ITERATIONS = 20

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    sheet_url: str
    iterations: int
    rows: int
    gaps: int


def run_agent(sow_data: dict, template: dict, provider: LLMProvider, sheets_writer) -> RunResult:
    """
    Runs the agentic loop. Returns a RunResult with sheet_url, iterations, rows, and gaps.
    sow_data: {"text": str, "images": [{"data": base64, "mime_type": str, "page": int, "index": int}]}
    template: {"columns": list[str], "sample_rows": list[dict]}
    """
    system = build_system_prompt(columns=template["columns"])
    tools = get_tool_schemas()
    executor = ToolExecutor(sheets_writer=sheets_writer, provider=provider)

    initial_content = _build_initial_content(sow_data, template)
    messages = [{"role": "user", "content": initial_content}]

    sheet_url = None
    rows_written = 0
    completed_iterations = 0

    for iteration in range(MAX_ITERATIONS):
        logger.info("iteration %d starting", iteration + 1)
        start = time.time()

        response = provider.complete(system=system, messages=messages, tools=tools)

        completed_iterations = iteration + 1

        if response.text is not None and not response.tool_calls:
            logger.info(
                "iteration %d: tools=%s latency_ms=%d",
                iteration + 1,
                ["<text>"],
                int((time.time() - start) * 1000),
            )
            logger.info("agent complete after %d iteration(s)", iteration + 1)
            break

        messages = provider.add_assistant_turn(messages, response)

        results = []
        for tool_call in response.tool_calls:
            output = executor.execute(tool_call.name, tool_call.arguments)
            results.append(ToolResult(
                call_id=tool_call.id,
                name=tool_call.name,
                content=output,
            ))
            if tool_call.name == "write_to_sheet" and "docs.google.com" in output:
                sheet_url = output
                rows_written = len(tool_call.arguments.get("rows", []))

        logger.info(
            "iteration %d: tools=%s latency_ms=%d",
            iteration + 1,
            [tc.name for tc in response.tool_calls] or ["<text>"],
            int((time.time() - start) * 1000),
        )

        messages = provider.add_tool_results(messages, results)
    else:
        raise RuntimeError(
            f"Agent exceeded maximum iterations ({MAX_ITERATIONS}). "
            "Check the SoW for content that may be causing the agent to loop."
        )

    if sheet_url is None:
        logger.warning("agent finished but wrote no sheet")
        raise RuntimeError("Agent completed without calling write_to_sheet. No Google Sheet was created.")

    return RunResult(
        sheet_url=sheet_url,
        iterations=completed_iterations,
        rows=rows_written,
        gaps=len(executor.gaps),
    )


def _build_initial_content(sow_data: dict, template: dict) -> list:
    columns_str = ", ".join(template["columns"])
    text_part = {
        "type": "text",
        "text": (
            f"Here is the Statement of Work:\n\n{sow_data['text']}\n\n"
            f"The output Google Sheet must use these columns exactly: {columns_str}\n\n"
            "Analyze the SoW and create a project plan. "
            "For any architecture diagrams, call analyze_diagram first. "
            "Only include deliverables you can trace directly to this SoW. "
            "Call write_to_sheet once with all rows when done."
        ),
    }
    content = [text_part]

    for img in sow_data.get("images", []):
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": img.get("mime_type", "image/png"),
                "data": img["data"],
            },
        })

    return content
