import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .trust import RubixTrustService


def load_nft_config() -> dict:
    """
    Load NFT settings (paths + value + init data) from env,
    with defaults suitable for the pickleball demo.
    """
    return {
        "artifact_path": os.getenv("NFT_ARTIFACT_PATH", "artifacts/pickleball.json"),
        "metadata_path": os.getenv("NFT_METADATA_PATH", "artifacts/pickleball-meta.json"),
        "value": float(os.getenv("NFT_VALUE", "0.001")),
        "data": os.getenv("NFT_INIT_DATA", "init data"),
    }


class RubixMessageHandler:
    """
    High-level Rubix helper for A2A agents.

    It exposes ONLY two main calls for developers:

      - build(...)
      - handle(...)

    and hides all Rubix / NFT details inside.

    Usage patterns
    --------------

    1) Host → Remote: build the signed host block, then embed into A2A message:

        dna = RubixMessageHandler(alias="host")

        built = dna.build(
            kind="host_request",
            original_message=task_text,
            state={"task_id": task_id, "context_id": context_id},  # optional
        )

        # built["host_json"] is what you put into the A2A text part
        host_json   = built["host_json"]
        message_id  = built["message_id"]
        context_id  = built["context_id"]

        # A2A payload (example)
        payload = {
            "message": {
                "role": "user",
                "parts": [
                    {"type": "text", "text": host_json},
                ],
                "messageId": message_id,
                "contextId": context_id,
            }
        }

    2) Remote agent (Karley / Nate / Kaitlyn) when receiving a message:

        dna = RubixMessageHandler(alias="karley", enable_nft=False)

        verify_info = await dna.handle(
            kind="incoming_request",
            raw_text=raw_from_context,
            verify_mode="light",   # or "heavy" in future
        )

        original_message = verify_info["original_message"]
        host_block       = verify_info["host_block"]
        host_ok          = verify_info["host_ok"]
        trust_issues     = verify_info["trust_issues"]

        # Use original_message for your local LLM/ADK agent

    3) Remote agent → Host: sign its response in a symmetric way:

        built_resp = dna.build(
            kind="agent_response",
            original_message=original_message,
            response=agent_result,
            host_block=host_block,
            extra={"host_trust_issues": trust_issues},
        )

        # Put built_resp["combined_json"] into your A2A text part

    4) Host handling remote responses (verify + optional NFT):

        result = await dna.handle(
            kind="host_response",
            resp_parts=resp_parts,      # list of {"text": "..."} from A2A artifacts
            original_task=task_text,
            remote_name=agent_name,
            execute_nft=True,           # will store in NFT if verification passes
        )

        messages     = result["messages"]      # verified messages w/ host+agent blocks
        trust_issues = result["trust_issues"]  # any issues
        nft_result   = result["nft_result"]    # optional: NFT execution response / None
    """

    def __init__(
        self,
        alias: str,
        token_filename: str = "token.txt",
        trust_service: Optional[RubixTrustService] = None,
        enable_nft: bool = True,
    ) -> None:
        # Trust layer (sign + verify + verify_message_payload)
        self.trust = trust_service or RubixTrustService(alias=alias)
        self.did = self.trust.did
        self.signer = self.trust.signer

        # NFT config
        self.enable_nft = enable_nft
        self.nft_cfg = load_nft_config()
        self.last_parts: List[Dict[str, Any]] = []

        # Where to store NFT token (host project, not site-packages)
        self.token_path: Optional[Path] = None
        self.nft_token: Optional[str] = None

        if self.enable_nft:
            env_path = os.getenv("AGENTDNA_TOKEN_PATH")
            if env_path:
                self.token_path = Path(env_path)
            else:
                project_root = Path.cwd()   # e.g. /.../host_agent_adk
                token_dir = project_root / ".agentdna"
                token_dir.mkdir(parents=True, exist_ok=True)
                self.token_path = token_dir / token_filename

            print("Path:", self.token_path)
            self.nft_token = self._load_or_deploy_nft()
            print("✅ Rubix NFT for alias", alias, ":", self.nft_token)
        else:
            print("ℹ️ RubixMessageHandler(enable_nft=False) – NFT operations disabled")

    # ======================================================================
    # Public API: BUILD
    # ======================================================================

    def build(
        self,
        *,
        kind: str,
        original_message: str,
        state: Optional[Dict[str, Any]] = None,
        response: Optional[str] = None,
        host_block: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Unified build() method.

        kind:
          - "host_request"   : host builds + signs a host envelope
          - "agent_response" : remote builds + signs its agent envelope and
                               combines it with the host block
        """
        kind = (kind or "").lower().strip()
        state = state or {}
        extra = extra or {}
        print(f"[RubixMessageHandler.build] kind={kind}")
        if kind == "host_request":
            # host → remote
            return self._build_host_request(
                original_message=original_message,
                state=state,
            )

        if kind == "agent_response":
            # remote → host
            if response is None:
                raise ValueError("build(kind='agent_response') requires `response`.")
            return self._build_agent_response(
                original_message=original_message,
                response=response,
                host_block=host_block,
                extra=extra,
            )

        raise ValueError(f"Unsupported build kind: {kind}")
    # ======================================================================
    # API: HANDLE
    # ======================================================================

    async def handle(
        self,
        *,
        kind: str,
        raw_text: Optional[str] = None,
        resp_parts: Optional[List[Dict[str, Any]]] = None,
        original_task: Optional[str] = None,
        remote_name: Optional[str] = None,
        verify_mode: str = "light",
        execute_nft: bool = True,
    ) -> Dict[str, Any]:
        kind = (kind or "").lower().strip()

        if kind == "remote":
            # remote agent handling inbound from host
            if raw_text is None:
                raise ValueError("handle(kind='remote') requires raw_text.")
            return self.trust.verify_message_payload(raw_text=raw_text, mode=verify_mode)

        if kind == "host":
            # host handling inbound from remote
            if resp_parts is None or original_task is None or remote_name is None:
                raise ValueError(
                    "handle(kind='host') requires resp_parts, original_task, remote_name."
                )
            return await self._handle_host_response(
                resp_parts=resp_parts,
                original_task=original_task,
                remote_name=remote_name,
                execute_nft=execute_nft,
            )

        raise ValueError(f"Unsupported handle kind: {kind}")

    # ======================================================================
    # Internal: host request building
    # ======================================================================

    def _build_host_request(
        self,
        original_message: str,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        task_id = state.get("task_id") or str(uuid.uuid4())
        context_id = state.get("context_id") or str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        host_envelope = {
            "original_message": original_message,
            "task_id":          task_id,
            "context_id":       context_id,
            "message_id":       message_id,
            "timestamp":        datetime.utcnow().isoformat() + "Z",
        }

        host_block = self.trust.sign_envelope(host_envelope)

        host_json = json.dumps(
            {"host": host_block},
            separators=(",", ":"),
            sort_keys=True,
        )

        return {
            "kind":        "host_request",
            "host_block":  host_block,
            "host_json":   host_json,
            "task_id":     task_id,
            "context_id":  context_id,
            "message_id":  message_id,
        }

    # ======================================================================
    # Internal: agent response building
    # ======================================================================

    def _build_agent_response(
        self,
        original_message: str,
        response: str,
        host_block: Optional[Dict[str, Any]],
        extra: Dict[str, Any],
    ) -> Dict[str, Any]:
        envelope = {
            "original_message": original_message,
            "response":         response,
        }
        # Optionally attach trust metadata (e.g. host_trust_issues)
        envelope.update(extra)

        agent_block = self.trust.sign_envelope(envelope)

        combined: Dict[str, Any] = {
            "agent": agent_block,
        }
        if host_block is not None:
            combined["host"] = host_block

        combined_json = json.dumps(
            combined,
            separators=(",", ":"),
            sort_keys=True,
        )

        return {
            "kind":          "agent_response",
            "host_block":    host_block,
            "agent_block":   agent_block,
            "envelope":      envelope,
            "combined_json": combined_json,
        }

    # ======================================================================
    # Internal: NFT helpers
    # ======================================================================

    def execute_nft(self, nft_address: str, payload: Any) -> Dict[str, Any]:
        """
        Execute an NFT using the signer from the trust service.
        """
        nft_data = json.dumps(payload)

        try:
            print("NFT address:", nft_address)
            print("NFT data:", nft_data)
            response = self.signer.execute_nft(
                nft_address=nft_address,
                nft_data=nft_data,
            )
        except Exception as e:
            raise RuntimeError(f"Rubix execute_nft call failed: {e}")

        if not response.get("status", False):
            raise RuntimeError(
                f"NFT Execution Failed: {response.get('message', '<no message>')}"
            )

        return response

    def _load_or_deploy_nft(self) -> str:
        if not self.token_path:
            raise RuntimeError("NFT token path not initialized (enable_nft=False?)")

        if self.token_path.exists():
            token = self.token_path.read_text(encoding="utf-8").strip()
            if token:
                print("ℹ️ Using existing NFT token:", token)
                return token
            else:
                print(f"⚠️ {self.token_path} is empty, deploying new NFT…")
        else:
            print(f"⚠️ token.txt not found at {self.token_path}, deploying new NFT…")

        print("Creating a new NFT")
        print("Artifact path:", self.nft_cfg["artifact_path"])
        print("Metadata path:", self.nft_cfg["metadata_path"])

        resp = self.signer.deploy_nft(
            artifact_file=self.nft_cfg["artifact_path"],
            metadata_file=self.nft_cfg["metadata_path"],
            nft_value=self.nft_cfg["value"] or 0.001,
            nft_data=self.nft_cfg["data"] or "init data",
        )
        if resp.get("error"):
            raise RuntimeError(f"NFT deployment failed: {resp['error']}")

        nft_address = resp["nft_address"]
        self.token_path.write_text(nft_address, encoding="utf-8")
        print("🚀 Deployed new NFT:", nft_address)
        return nft_address

    # ======================================================================
    # Internal: host handling remote responses
    # ======================================================================

    async def _handle_host_response(
        self,
        resp_parts: List[Dict[str, Any]],
        original_task: str,
        remote_name: str,
        execute_nft: bool,
    ) -> Dict[str, Any]:
        """
        Old handle_response_parts, but wrapped into handle(kind="host_response").
        """
        verified: List[Dict[str, Any]] = []
        trust_issues: List[str] = []
        error_msg: Optional[str] = None
        nft_result: Optional[Dict[str, Any]] = None

        for part in resp_parts:
            raw_text = part.get("text") or part.get("content", "")
            try:
                payload = json.loads(raw_text)
            except (TypeError, json.JSONDecodeError):
                continue

            # Expect {"host": {...}, "agent": {...}}
            if not isinstance(payload, dict) or "agent" not in payload:
                continue

            host_block = payload.get("host")
            agent_block = payload["agent"]

            signer_did = agent_block.get("agent")
            env = agent_block.get("envelope", {})
            sig = agent_block.get("signature")

            if not (signer_did and env and sig):
                trust_issues.append("Missing fields in agent block")
                print("Missing fields in agent block")
                continue

            # verify via trust service
            if not self.trust.verify_envelope(signer_did, env, sig):
                trust_issues.append(f"Invalid signature from {signer_did}")
                print(f"Invalid signature from {signer_did}")
                continue

            # Optional consistency check
            if env.get("original_message") != original_task:
                trust_issues.append("Original message mismatch")
                print("Original message mismatch")

            verified.append(
                {
                    "host": host_block,
                    "agent": agent_block,
                    "agent_sig_valid": True,
                }
            )
            print("Verified agent block from", signer_did)

        if not verified and not trust_issues:
            error_msg = "No valid envelope response"
            print("No valid envelope response")

        self.last_parts = verified

        # Optional NFT execution on host
        if (
            self.enable_nft
            and execute_nft
            and verified
            and self.nft_token is not None
        ):
            try:
                payload = self._build_nft_payload(remote_name)
                nft_result = await asyncio.to_thread(
                    self.execute_nft,
                    self.nft_token,
                    payload,
                )
                print("🚀 NFT execution result:", nft_result)
            except Exception as e:
                print("⚠️ NFT execution failed:", e)

        return {
            "messages": verified,
            "trust_issues": trust_issues or None,
            "error": error_msg,
            "nft_result": nft_result,
        }

    def _build_nft_payload(self, remote_name: str) -> Dict[str, Any]:
        """
        Build the JSON that will be stored in the NFT.
        """
        host_block = None
        responses: List[Dict[str, Any]] = []
        for entry in self.last_parts:
            if not host_block and entry.get("host"):
                host_block = entry["host"]
            if entry.get("agent"):
                responses.append(entry["agent"])

        return {
            "comment":  f"Pickleball scheduling with {remote_name}",
            "executor": "host_agent",
            "did":      self.did,
            "host":     host_block,
            "responses": responses,
        }