from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List


@lru_cache(maxsize=1)
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _martian_cli_path() -> Path:
    return _repo_root() / "scripts" / "martian_cli.mjs"


@lru_cache(maxsize=1)
def _node_bin() -> str:
    import shutil

    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js >= 18 is required. Run `npm ci` at repo root.")
    return node


@dataclass(frozen=True)
class MartianRunner:
    node_path: str = _node_bin()
    cli_path: Path = _martian_cli_path()
    timeout_sec: int = 120

    def run(self, markdown: str) -> List[Dict[str, Any]]:
        if not self.cli_path.exists():
            raise FileNotFoundError(f"Martian CLI not found at {self.cli_path}")
        proc = subprocess.run(
            [self.node_path, str(self.cli_path), "--stdin"],
            input=markdown.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            check=False,
            timeout=self.timeout_sec,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", errors="replace"))
        out = proc.stdout.decode("utf-8", errors="replace")
        try:
            blocks = json.loads(out)
        except json.JSONDecodeError as e:
            stderr = proc.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"{stderr}\n{out[:5000]}") from e
        if not isinstance(blocks, list):
            raise RuntimeError("Martian output is not a list")
        return blocks
