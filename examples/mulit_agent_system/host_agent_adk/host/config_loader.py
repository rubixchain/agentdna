
from __future__ import annotations
from pathlib import Path
import os, json
from typing import Any, Dict

def _find_cfg(start: Path, filename: str = "config.json", max_up: int = 5) -> Path:
    """Search upward from `start` for `filename`, up to `max_up` parents."""
    p = start.resolve()
    for _ in range(max_up + 1):
        cand = p / filename
        if cand.exists():
            return cand
        if p.parent == p:
            break
        p = p.parent
    raise FileNotFoundError(f"{filename} not found starting at {start}")

def _default_cfg_path() -> Path:
    return _find_cfg(Path(__file__).parent)

def load_config(path: str | os.PathLike | None = None) -> Dict[str, Any]:
    cfg_path = Path(os.getenv("CONFIG_PATH") or path or _default_cfg_path())
    with cfg_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_nft_config(path: str | os.PathLike | None = None) -> Dict[str, Any]:
    cfg = load_config(path).get("nft", {})
    return {
        "metadata_path": cfg.get("metadata_path", ""),
        "artifact_path": cfg.get("artifact_path", ""),
        "password":      cfg.get("password", ""),
        "base_url":      cfg.get("base_url", ""),
        "timeout":       float(cfg.get("timeout", 100.0)),
        "data":          cfg.get("data", ""),
        "value":         int(cfg.get("value", 0)),
        "quorum_type":   int(cfg.get("quorum_type", 2)),
    }