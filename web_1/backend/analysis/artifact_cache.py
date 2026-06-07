"""Simple content-addressed cache for expensive analysis stages."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _stable_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class ArtifactCache:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.schema_version = "v2"

    def build_stage_key(
        self,
        stage: str,
        *,
        file_paths: list[Path],
        params: dict[str, Any],
        file_roles: list[str] | None = None,
    ) -> str:
        roles = file_roles or [f"input_{idx}" for idx in range(len(file_paths))]
        if len(roles) != len(file_paths):
            raise ValueError("file_roles length must match file_paths")
        payload = {
            "schema_version": self.schema_version,
            "stage": stage,
            "files": [{"role": role, "sha256": _sha256_file(p)} for role, p in zip(roles, file_paths)],
            "params": params,
        }
        return _stable_hash(payload)

    def _stage_dir(self, stage: str, key: str) -> Path:
        return self.root / stage / key

    def restore(self, stage: str, key: str, outputs: dict[str, Path]) -> bool:
        src_dir = self._stage_dir(stage, key)
        if not src_dir.is_dir():
            return False
        for name, dst in outputs.items():
            src = src_dir / name
            if not src.exists():
                return False
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return True

    def save(self, stage: str, key: str, outputs: dict[str, Path], meta: dict[str, Any] | None = None) -> None:
        dst_dir = self._stage_dir(stage, key)
        dst_dir.mkdir(parents=True, exist_ok=True)
        for name, src in outputs.items():
            target = dst_dir / name
            if src.exists():
                shutil.copy2(src, target)
        if meta is not None:
            (dst_dir / "_meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )
