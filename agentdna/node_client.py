from __future__ import annotations
from pathlib import Path
import os, json, requests
from typing import Any, Dict, Optional, List

class NodeClient:
    """
    Minimal client for your local node.
    Resolve base_url from (in order): explicit base_url -> framework name -> port -> config.json -> ENV.
    """

    def __init__(
        self,
        alias: Optional[str] = None, 
        base_url: Optional[str] = None,
        config_path: Optional[Union[str, Path]] = None,
    ):
        if not config_path:
          
            config_path = Path(__file__).resolve().parent.parent / "config.json"

        print("config path:", config_path)

        port = self._read_port(alias, config_path)

        self.base_url = (
            base_url
            or os.getenv("BASE_URL")
            or f"http://localhost:{port or self._read_port_from_config(alias, config_path)}"
        )

    def get_base_url(self) -> str:
        return self.base_url

    
    @staticmethod
    def _read_port(alias: str, config_path: Optional[Union[str, Path]]) -> Optional[int]:
        """
        Reads the port from config.json for the given framework name.
        Example: framework="host" → key="host_port"
        """
        path = Path(os.getenv("CONFIG_PATH") or (config_path or NodeClient._default_config_path()))
        try:
            with Path(path).open("r", encoding="utf-8") as f:
                cfg = json.load(f)
            key = f"{alias.lower()}"
            return int(cfg.get(key))
        except Exception:
            return None

    @staticmethod
    def _read_port_from_config(alias: str, config_path: Optional[Union[str, Path]]) -> Optional[int]:
        """
        Fallback to reading generic port or langgraph_port if no framework given.
        """
        path = Path(os.getenv("CONFIG_PATH") or (config_path or NodeClient._default_config_path()))
        try:
            with Path(path).open("r", encoding="utf-8") as f:
                cfg = json.load(f)
            return int(cfg.get("port") or cfg.get(alias))
        except Exception:
            return None

    @staticmethod
    def _default_config_path() -> Path:
        here = Path(__file__).resolve()
        return here.parents[2] / "config.json"