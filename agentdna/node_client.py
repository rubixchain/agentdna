from __future__ import annotations
from pathlib import Path
import os, json, requests
from typing import Any, Dict, Optional, List, Union

class NodeClient:
    """
    Minimal client that resolves Rubix node URL from:
    1. explicit base_url
    2. explicit chain_url
    3. config.json -> chain_url
    4. CHAIN_URL env var
    """

    def __init__(
        self,
        alias: Optional[str] = None,
        base_url: Optional[str] = None,
        chain_url: Optional[str] = None,
        config_path: Optional[Union[str, Path]] = None,
    ):
        if config_path is None:
            config_path = Path(__file__).resolve().parent / "config.json"

        print("config path:", config_path)

        cfg_chain = self._read_chain_url(config_path)
        print("Config Chain:", cfg_chain)

        final_url = base_url or chain_url or cfg_chain or os.getenv("CHAIN_URL")

        if not final_url:
            raise ValueError(
                "No Rubix node URL found. Set chain_url, config.json['chain_url'], or CHAIN_URL."
            )

        self.base_url = final_url.rstrip("/")
        print("Final Chain URL:", self.base_url)

    @staticmethod
    def _read_chain_url(config_path: Union[str, Path]) -> Optional[str]:
        try:
            with Path(config_path).open("r", encoding="utf-8") as f:
                cfg = json.load(f)
            return cfg.get("chain_url")
        except Exception:
            return None

    def get_base_url(self) -> str:
        return self.base_url