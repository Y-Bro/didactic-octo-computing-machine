from agent.prompt import build_system_prompt
from agent.tools import get_tool_schemas, ToolExecutor
from agent.providers.base import LLMProvider, ToolResult

MAX_ITERATIONS = 20


def run_agent(sow_data: dict, template: dict, provider: LLMProvider, sheets_writer) -> str:
    """
    Runs the agentic loop. Returns the Google Sheet URL.
    sow_data: {"text": str, "images": [{"data": base64, "mime_type": str, "page": int, "index": int}]}
    template: {"columns": list[str], "sample_rows": list[dict]}
    """
    system = build_system_prompt(columns=template["columns"])
    tools = get_tool_schemas()
    executor = ToolExecutor(sheets_writer=sheets_writer, provider=provider)

    initial_content = _build_initial_content(sow_data, template)
    messages = [{"role": "user", "content": initial_content}]

    sheet_url = None

    for iteration in range(MAX_ITERATIONS):
        response = provider.complete(system=system, messages=messages, tools=tools)

        if response.text is not None and not response.tool_calls:
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

        messages = provider.add_tool_results(messages, results)
    else:
        raise RuntimeError(
            f"Agent exceeded maximum iterations ({MAX_ITERATIONS}). "
            "Check the SoW for content that may be causing the agent to loop."
        )

    if sheet_url is None:
        raise RuntimeError("Agent completed without calling write_to_sheet. No Google Sheet was created.")

    return sheet_url


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
