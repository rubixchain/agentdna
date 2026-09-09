from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias

# Function interface for CBAC service entry-point function
CbacFn: TypeAlias = Callable[
    [
        # Agent ID: Agent which is making the request to resource
        str,
        # MCP Server ID: The identifier or address of the MCP server sending the request
        str,
        # Tool Name: Name of the tool being invoked
        str,
        # Tool Argument: Arguments passed to the tool
        dict[str, Any],
        # User Intent: The intent of the user making the request
        str | None,
        # Tool Description: Description of the tool being invoked.
        # Its normally taken from the tool's comments. Hence, empty
        # values are accepted.
        str | None,
        # Intent ID: The identifier of the user intent associated with the request.
        str | None,
    ],
    Awaitable[
        tuple[
            # Decision: The decision made by the CBAC server.
            # The value "allow" should be sent for an Allow decision since
            # the AgentDNA middleware relies on this value to enforce access control decisions.
            str,
            # Status Code: The HTTP-like status code representing the result of the CBAC decision.
            int,
            # Message Hash: It represent the hash of the message associated with the CBAC decision.
            # It is not encouraged to share the actual information contained in the message, since
            # it may have PII information, which should not be stored directly on the Provenance layer
            str,
        ]
    ],
]


class CBACVerificationError(Exception):
    """Raised when CBAC verification fails."""

    pass
