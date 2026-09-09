from __future__ import annotations

from typing import Any

from crewai.tools import BaseTool
from crewai_tools import MCPServerAdapter
from agentdna.mcp.client.crewai import install_mcp_client
from config import settings


install_mcp_client()

def build_client() -> MCPServerAdapter:
    return MCPServerAdapter(
        {
            "url": settings.sqlite_mcp_url,
            "transport": "streamable-http",
            "headers": getattr(
                settings,
                "sqlite_mcp_headers",
                {},
            ),
        },
        connect_timeout=settings.mcp_timeout_seconds,
    )


def load_tools() -> list[BaseTool]:
    """
    Discover the SQLite capabilities through CrewAI's native MCP client.
    """

    client = build_client()

    try:
        discovered = {
            tool.name: tool
            for tool in client.tools
        }

        required = {
            "sqlite_list_tables",
            "sqlite_describe_table",
            "sqlite_query",
        }

        missing = required.difference(
            discovered
        )

        if missing:
            raise RuntimeError(
                "SQLite MCP server did not expose expected tools: "
                f"{sorted(missing)}"
            )

        return [
            discovered["sqlite_list_tables"],
            discovered["sqlite_describe_table"],
            discovered["sqlite_query"],
        ]

    except Exception:
        client.stop()
        raise