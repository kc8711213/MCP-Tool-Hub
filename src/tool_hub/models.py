from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RegisteredTool(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tool_id: str
    server_id: str
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DownstreamServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)


class HubConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    servers: list[DownstreamServerConfig] = Field(default_factory=list)
    default_tool_tags: list[str] = Field(default_factory=list)
    mock_mode: bool = False


class SearchResult(BaseModel):
    tool_id: str
    server_id: str
    name: str
    description: str
    tags: list[str]
    score: int
    usage_instruction: str


class InvokeResult(BaseModel):
    tool_id: str
    server_id: str
    result: Any

