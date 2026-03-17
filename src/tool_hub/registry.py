from __future__ import annotations

from dataclasses import dataclass

from .models import RegisteredTool, SearchResult


@dataclass(frozen=True)
class SearchWeights:
    name: int = 3
    tags: int = 2
    description: int = 1


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: RegisteredTool) -> None:
        self._tools[tool.tool_id] = tool

    def bulk_register(self, tools: list[RegisteredTool]) -> None:
        for tool in tools:
            self.register(tool)

    def get(self, tool_id: str) -> RegisteredTool:
        try:
            return self._tools[tool_id]
        except KeyError as exc:
            raise KeyError(f"Unknown tool_id: {tool_id}") from exc

    def list_tools(self, server_id: str | None = None) -> list[RegisteredTool]:
        tools = self._tools.values()
        if server_id is not None:
            tools = [tool for tool in tools if tool.server_id == server_id]
        return sorted(tools, key=lambda item: (item.server_id, item.name))

    def search(
        self,
        query: str,
        top_k: int = 5,
        weights: SearchWeights | None = None,
    ) -> list[SearchResult]:
        weights = weights or SearchWeights()
        terms = [term.casefold() for term in query.split() if term.strip()]
        if not terms:
            return []

        scored: list[SearchResult] = []
        for tool in self._tools.values():
            score = self._score_tool(tool, terms, weights)
            if score <= 0:
                continue
            scored.append(
                SearchResult(
                    tool_id=tool.tool_id,
                    server_id=tool.server_id,
                    name=tool.name,
                    description=tool.description,
                    tags=tool.tags,
                    score=score,
                    usage_instruction=(
                        f"Use invoke_tool(tool_id='{tool.tool_id}', arguments={{...}})"
                    ),
                )
            )

        scored.sort(key=lambda item: (-item.score, item.server_id, item.name))
        return scored[:top_k]

    @staticmethod
    def _score_tool(
        tool: RegisteredTool,
        terms: list[str],
        weights: SearchWeights,
    ) -> int:
        name = tool.name.casefold()
        tags = [tag.casefold() for tag in tool.tags]
        description = tool.description.casefold()
        score = 0

        for term in terms:
            if term in name:
                score += weights.name
            if any(term in tag for tag in tags):
                score += weights.tags
            if term in description:
                score += weights.description

        return score

