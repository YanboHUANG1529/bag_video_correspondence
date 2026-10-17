"""Copy selected local inputs and verify hashes; never replace differing data."""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
from common import PROJECT, contained, read_json, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = read_json(PROJECT / "configs/local_sources.json")
    root = (args.source_root or PROJECT / config["source_root_relative_to_project"]).resolve()
    bundle = contained(root, config["upstream_bundle"])
    upstream = read_json(bundle / "MANIFEST.json")
    known = {row["path"]: row["sha256"] for row in upstream["files"]}
    selected = {}
    for group in config["imports"]:
        base = bundle if group["base"] == "bundle" else root
        source = contained(base, group["source"])
        if not source.exists():
            raise FileNotFoundError(source)
        if source.is_file():
            files = [source]
        elif "patterns" in group:
            files = sorted({p for pattern in group["patterns"] for p in source.glob(pattern) if p.is_file()})
        else:
            files = sorted(p for p in source.rglob("*") if p.is_file())
        if not files:
            raise ValueError("Empty import group: " + group["source"])
        for path in files:
            target = group["destination"]
            if source.is_dir():
                target += "/" + path.relative_to(source).as_posix()
            if target in selected and selected[target] != path:
                raise ValueError("Conflicting import destination: " + target)
            selected[target] = path
    if args.dry_run:
        print(json.dumps({"selected_files": len(selected), "bytes": sum(p.stat().st_size for p in selected.values())}))
        return
    rows, copied, reused = [], 0, 0
    for destination, source in sorted(selected.items()):
        digest = sha256(source)
        try:
            upstream_path = source.relative_to(bundle).as_posix()
        except ValueError:
            upstream_path = None
        expected = known.get(upstream_path)
        if expected is not None and digest != expected:
            raise ValueError("Upstream SHA-256 mismatch: " + str(upstream_path))
        target = contained(PROJECT, destination)
        if target.exists():
            if sha256(target) != digest:
                raise FileExistsError("Local copy differs; resolve explicitly: " + destination)
            reused += 1
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            handle, temporary = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
            os.close(handle)
            try:
                shutil.copy2(source, temporary)
                if sha256(temporary) != digest:
                    raise ValueError("Copy verification failed: " + destination)
                os.replace(temporary, target)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            copied += 1
        rows.append({"source_repository_relative": source.relative_to(root).as_posix(),
                     "destination": destination, "bytes": source.stat().st_size,
                     "sha256": digest, "upstream_manifest_verified": expected is not None})
    manifest = {"schema_version": 1, "case_id": "case00", "mode": "independent_copies",
                "source_config": "configs/local_sources.json", "files": rows,
                "summary": {"file_count": len(rows), "total_bytes": sum(r["bytes"] for r in rows),
                            "upstream_verified_count": sum(r["upstream_manifest_verified"] for r in rows)}}
    write_json(PROJECT / "data/manifests/local_data_manifest.json", manifest)
    print(json.dumps({"copied": copied, "reused": reused, **manifest["summary"]}))


if __name__ == "__main__":
    main()
