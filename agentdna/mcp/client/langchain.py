from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from agentdna.mcp.context import get_context
from agentdna.mcp.metadata import (
    workflow_from_metadata,
    workflow_to_metadata,
)
from agentdna.types import RESULT_OK

_PATCH_INSTALLED = False


def install_mcp_client() -> None:
    """
    Install AgentDNA integration into langchain-mcp-adapters.

    The LangChain MCP adapter continues to own transport creation,
    session lifecycle, tool discovery, LangChain tool construction,
    result conversion, and framework-level error handling.

    AgentDNA only instruments actual MCP tools/call requests.
    """

    global _PATCH_INSTALLED

    if _PATCH_INSTALLED:
        return

    try:
        import langchain_mcp_adapters.sessions as sessions
        import langchain_mcp_adapters.tools as tools
    except ImportError as exc:
        raise ImportError("langchain-mcp-adapters is not installed.") from exc

    original_create_session = sessions.create_session

    @asynccontextmanager
    async def _agentdna_create_session(
        connection: Any,
        *args: Any,
        **kwargs: Any,
    ):
        async with original_create_session(
            connection,
            *args,
            **kwargs,
        ) as session:
            _install_session_call_tool_patch(session)
            yield session

    # tools.py imports create_session directly, so both references
    # must be patched.
    sessions.create_session = _agentdna_create_session

    tools.create_session = _agentdna_create_session

    _PATCH_INSTALLED = True


def _install_session_call_tool_patch(session: Any) -> None:
    """
    Patch one concrete MCP ClientSession instance.

    Patching the concrete session avoids modifying the MCP SDK globally.
    """

    if getattr(session, "_agentdna_call_tool_patched", False):
        return

    original_call_tool = session.call_tool

    async def agentdna_call_tool(
        name: str,
        arguments: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        context = get_context()

        # Normal LangChain/MCP execution when AgentDNA context is absent.
        if context is None:
            return await original_call_tool(
                name,
                arguments,
                *args,
                **kwargs,
            )

        # One actual MCP tools/call request = one AgentDNA workflow.
        call_handle = await context.begin_mcp_call()
        parent_frontier = list(call_handle.batch.parent_frontier)

        try:
            request_payload = build_mcp_tool_call_payload(
                name=name,
                arguments=arguments,
            )

            request_workflow = context.dna.build(
                payload=request_payload,
                previous_workflows=parent_frontier,
                verification_code=RESULT_OK,
            )

            request_meta = workflow_to_metadata(request_workflow)

            # Preserve metadata supplied by the caller while allowing
            # AgentDNA to own its own namespace.
            existing_meta = kwargs.pop("meta", None)

            merged_meta = _merge_mcp_metadata(
                existing_meta,
                request_meta,
            )

            result = await original_call_tool(
                name,
                arguments,
                *args,
                meta=merged_meta,
                **kwargs,
            )

        except Exception:
            # The MCP call itself raised an exception. There is no
            # response workflow to process, so cancel this call and
            # preserve the original exception.
            await context.cancel_mcp_call(call_handle)
            raise

        # ------------------------------------------------------------
        # MCP-level error result.
        #
        # The server may turn a middleware exception into:
        #
        #   CallToolResult(is_error=True, content=[...])
        #
        # In that case there is intentionally no successor workflow.
        # Extract the server's message and propagate it to LangChain.
        # ------------------------------------------------------------

        is_error = getattr(result, "is_error", None)

        if is_error is None:
            is_error = getattr(result, "isError", False)

        if is_error:
            await context.cancel_mcp_call(call_handle)

            error_message = _extract_result_text(result)

            if error_message:
                raise RuntimeError(error_message)

            raise RuntimeError("MCP tool call failed")

        # ------------------------------------------------------------
        # Successful MCP result.
        #
        # A successful AgentDNA-protected request MUST return the
        # successor workflow in MCP response metadata.
        # ------------------------------------------------------------

        successor = workflow_from_metadata(getattr(result, "meta", None))

        if successor is None:
            await context.cancel_mcp_call(call_handle)

            raise RuntimeError("MCP tool response did not contain an AgentDNA successor workflow")

        verification_code = context.dna.verify(successor)

        if verification_code != RESULT_OK:
            await context.cancel_mcp_call(call_handle)

            failed_workflow = context.dna.build(
                payload=f"CoCA: failed to verify signature for workflow received from the {successor.get_latest_envelope_actor()}",
                previous_workflows=successor,
                verification_code=verification_code,
            )
            context.dna.record(failed_workflow)

            raise ValueError(
                f"CoCA verification failed for workflow recieved from the {successor.get_latest_envelope_actor()}"
            )

        await context.complete_mcp_call(
            call_handle,
            successor,
        )

        return result

    session.call_tool = agentdna_call_tool

    session._agentdna_call_tool_patched = True


def _merge_mcp_metadata(
    existing_meta: dict[str, Any] | None,
    agentdna_meta: dict[str, Any],
) -> dict[str, Any]:
    """
    Merge AgentDNA metadata into existing MCP metadata.

    AgentDNA owns the "agentdna" namespace and preserves unrelated
    metadata supplied by the caller.
    """

    merged_meta = dict(existing_meta or {})

    existing_agentdna = dict(merged_meta.get("agentdna") or {})

    agentdna_section = agentdna_meta.get("agentdna")

    if isinstance(agentdna_section, dict):
        existing_agentdna.update(agentdna_section)

    merged_meta["agentdna"] = existing_agentdna

    return merged_meta


def _extract_result_text(
    result: Any,
) -> str | None:
    """
    Extract human-readable text from an MCP CallToolResult.
    """

    content = getattr(result, "content", None)

    if not content:
        return None

    messages: list[str] = []

    for item in content:
        text = getattr(item, "text", None)

        if isinstance(text, str) and text:
            messages.append(text)

    if not messages:
        return None

    return " | ".join(messages)


def build_mcp_tool_call_payload(
    name: str,
    arguments: dict[str, Any] | None,
) -> str:
    """
    Build the canonical AgentDNA representation of one MCP
    tools/call request.

    JSON-RPC framing is intentionally excluded.
    """

    return json.dumps(
        {
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments,
            },
        },
        separators=(",", ":"),
        sort_keys=True,
    )
