from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    call_id: str
    name: str
    content: str


@dataclass
class LLMResponse:
    tool_calls: list[ToolCall] = field(default_factory=list)
    text: str | None = None


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        """
        Single completion call. messages follow this format:
          {"role": "user", "content": str | list}      — user turn (list for multimodal)
          {"role": "assistant", "tool_calls": [...]}   — assistant tool request turn
          {"role": "tool", "results": [...]}           — tool results turn
        Returns LLMResponse with either tool_calls or text populated.
        """
        pass

    @abstractmethod
    def add_assistant_turn(self, messages: list[dict], response: LLMResponse) -> list[dict]:
        """Appends the assistant's tool-call turn to messages."""
        pass

    @abstractmethod
    def add_tool_results(self, messages: list[dict], results: list[ToolResult]) -> list[dict]:
        """Appends tool results to messages."""
        pass
