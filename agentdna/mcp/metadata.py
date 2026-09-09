from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from agentdna.types import (
    IntentWorkflow,
    load_workflow,
)

AGENTDNA_META_KEY = "agentdna"

AGENTDNA_INTENT_WORKFLOW_META_KEY = "intent_workflow"


def workflow_to_metadata(
    workflow: IntentWorkflow,
) -> dict[str, Any]:
    """
    Build the MCP `_meta` payload used for AgentDNA propagation.

    The returned Any is intended to be passed to an MCP client's
    `meta=` argument.
    """

    return {
        AGENTDNA_META_KEY: {
            AGENTDNA_INTENT_WORKFLOW_META_KEY: (workflow.serialize()),
        }
    }


def workflow_from_metadata_old(
    meta: object,
) -> IntentWorkflow | None:
    """
    Extract and deserialize an AgentDNA IntentWorkflow from
    MCP request/response metadata.
    """

    if not isinstance(
        meta,
        dict,
    ):
        return None

    agentdna = meta.get(AGENTDNA_META_KEY)

    if not isinstance(
        agentdna,
        dict,
    ):
        return None

    serialized_workflow = agentdna.get(AGENTDNA_INTENT_WORKFLOW_META_KEY)

    if (
        not isinstance(
            serialized_workflow,
            str,
        )
        or not serialized_workflow
    ):
        return None

    return load_workflow(json.loads(serialized_workflow))


def workflow_from_metadata(
    meta: object,
) -> IntentWorkflow | None:

    if meta is None:
        return None

    if hasattr(meta, "model_dump"):
        try:
            meta = meta.model_dump(by_alias=True)
        except Exception:
            return None

    if not isinstance(
        meta,
        Mapping,
    ):
        return None

    agentdna_meta = meta.get(AGENTDNA_META_KEY)

    if not isinstance(
        agentdna_meta,
        Mapping,
    ):
        return None

    workflow_data = agentdna_meta.get(AGENTDNA_INTENT_WORKFLOW_META_KEY)

    if not isinstance(
        workflow_data,
        str,
    ):
        return None

    try:
        data = json.loads(workflow_data)
    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None

    return load_workflow(data)


def workflow_to_metadata_json(
    workflow: IntentWorkflow,
) -> str:
    """
    Serialize AgentDNA MCP metadata as JSON.

    Primarily useful where an integration needs to temporarily
    transport the metadata through an intermediate representation.
    """

    return json.dumps(
        workflow_to_metadata(workflow),
        separators=(
            ",",
            ":",
        ),
        sort_keys=True,
    )
