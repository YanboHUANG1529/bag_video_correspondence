"""Small, project-local I/O helpers. Paths in manifests remain portable."""
from pathlib import Path
import hashlib
import json
import os
import tempfile

PROJECT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    handle, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contained(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError("Path escapes its configured root: " + str(relative)) from error
    return path


def load_obj(path):
    """Preserve raw OBJ vertex and face order; this bootstrap accepts triangles."""
    import numpy as np
    vertices, faces = [], []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "v":
            vertices.append([float(v) for v in fields[1:4]])
        elif fields[0] == "f":
            if len(fields) != 4:
                raise ValueError("Non-triangle OBJ needs an explicit face-index conversion")
            ids = [int(v.split("/")[0]) for v in fields[1:]]
            if 0 in ids:
                raise ValueError("OBJ indices cannot be zero")
            faces.append([v - 1 if v > 0 else len(vertices) + v for v in ids])
    vertices = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or faces.ndim != 2 or faces.shape[1] != 3:
        raise ValueError("Expected nonempty triangular OBJ")
    if not np.isfinite(vertices).all() or faces.min() < 0 or faces.max() >= len(vertices):
        raise ValueError("Invalid OBJ geometry or indices")
    return vertices, faces
