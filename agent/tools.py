import json


def get_tool_schemas() -> list[dict]:
    return [
        {
            "name": "analyze_diagram",
            "description": "Analyze an architecture diagram image and return structured JSON describing components, integrations, and system boundaries. Only call this for images from the SoW.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_base64": {
                        "type": "string",
                        "description": "Base64-encoded image data from the SoW",
                    },
                    "page_number": {
                        "type": "integer",
                        "description": "Page number where this diagram appears (use 0 if unknown)",
                    },
                },
                "required": ["image_base64", "page_number"],
            },
        },
        {
            "name": "write_to_sheet",
            "description": "Create a new Google Sheet with the project plan. Call this once when all deliverables have been identified. Pass all rows at once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title for the new Google Sheet",
                    },
                    "rows": {
                        "type": "array",
                        "description": "List of plan rows. Each row is a dict matching the template columns.",
                        "items": {"type": "object"},
                    },
                },
                "required": ["title", "rows"],
            },
        },
        {
            "name": "flag_gap",
            "description": "Record an ambiguous item, unclear scope, or anything that cannot be traced to the SoW. Call this instead of inventing a deliverable.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why this item is ambiguous or missing",
                    },
                    "location": {
                        "type": "string",
                        "description": "Where in the SoW this issue was found (e.g. 'Section 3', 'page 5', 'diagram on page 2')",
                    },
                },
                "required": ["reason", "location"],
            },
        },
    ]


class ToolExecutor:
    def __init__(self, sheets_writer, provider):
        self._writer = sheets_writer
        self._provider = provider
        self.gaps: list[dict] = []

    def execute(self, name: str, arguments: dict) -> str:
        if name == "analyze_diagram":
            return json.dumps(self.analyze_diagram(**arguments))
        if name == "write_to_sheet":
            return self.write_to_sheet(**arguments)
        if name == "flag_gap":
            return self.flag_gap(**arguments)
        raise ValueError(f"Unknown tool: {name}")

    def analyze_diagram(self, image_base64: str, page_number: int) -> dict:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "This is an architecture diagram from a Statement of Work. "
                            "Extract: (1) all named components/systems, (2) integrations between them, "
                            "(3) system boundaries. Return ONLY valid JSON in this format: "
                            '{"components": [...], "integrations": [...], "boundaries": [...]}'
                        ),
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_base64,
                        },
                    },
                ],
            }
        ]
        response = self._provider.complete(
            system="You are a technical diagram analyst. Respond only with valid JSON.",
            messages=messages,
            tools=[],
        )
        try:
            return json.loads(response.text)
        except (json.JSONDecodeError, TypeError):
            return {"components": [], "integrations": [], "boundaries": [], "parse_error": response.text}

    def write_to_sheet(self, title: str, rows: list[dict]) -> str:
        url = self._writer.create_sheet(title=title, rows=rows, gaps=self.gaps)
        return url

    def flag_gap(self, reason: str, location: str) -> str:
        self.gaps.append({"reason": reason, "location": location})
        return "Gap recorded."
