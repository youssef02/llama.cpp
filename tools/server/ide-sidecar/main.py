"""
llama.cpp IDE Sidecar  v0.3  (Podman)
======================================
Bridges the webui IDE + Model Manager to:
  - GGUF file discovery      GET /ide/gguf/scan?dir=...
  - Podman containers        /ide/containers/*
  - Code execution           POST /ide/containers/exec
  - Host filesystem          /ide/files/*  (sandboxed to cwd)

Uses the docker SDK pointed at Podman's Docker-compatible socket.
/ide/docker/* aliases kept for backward compatibility.

Setup:
    pip install fastapi uvicorn docker
    systemctl --user enable --now podman.socket   # Linux
    podman machine start                          # macOS / Windows
    python tools/server/ide-sidecar/main.py
"""
from __future__ import annotations

import io
import os
import tarfile
import time
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Podman socket discovery ────────────────────────────────────────────────

def _find_podman_socket() -> str:
    explicit = os.getenv("PODMAN_SOCKET")
    if explicit:
        return explicit
    uid = os.getuid() if hasattr(os, "getuid") else 0
    xdg = os.getenv("XDG_RUNTIME_DIR", f"/run/user/{uid}")
    candidates = [
        Path(f"/run/user/{uid}/podman/podman.sock"),
        Path(xdg) / "podman" / "podman.sock",
        Path.home() / ".local/share/containers/podman/machine/podman.sock",
        Path.home() / ".local/share/containers/podman/machine/qemu/podman.sock",
        Path("/run/podman/podman.sock"),
    ]
    for p in candidates:
        if p.exists() and p.is_socket():
            return f"unix://{p}"
    return "unix:///var/run/docker.sock"

PODMAN_SOCKET = _find_podman_socket()

try:
    import docker
    from docker.errors import NotFound, APIError
    _client = docker.DockerClient(base_url=PODMAN_SOCKET)
    _client.ping()
    PODMAN_AVAILABLE = True
    print(f"✓ Podman connected via {PODMAN_SOCKET}")
except Exception as _e:
    _client = None
    PODMAN_AVAILABLE = False
    print(f"⚠  Podman not available: {_e}")
    print(f"   Socket tried: {PODMAN_SOCKET}")
    print("   Linux : systemctl --user enable --now podman.socket")
    print("   macOS : podman machine start")

# ── Config ─────────────────────────────────────────────────────────────────

HOST    = os.getenv("IDE_SIDECAR_HOST", "0.0.0.0")
PORT    = int(os.getenv("IDE_SIDECAR_PORT", "8081"))
ORIGINS = os.getenv(
    "IDE_SIDECAR_ORIGINS",
    "http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:8080",
).split(",")
SANDBOX_ROOT   = Path(os.getenv("IDE_SIDECAR_ROOT", os.getcwd())).resolve()
GGUF_MAX_DEPTH = int(os.getenv("IDE_SIDECAR_GGUF_MAX_DEPTH", "4"))

# ── App ────────────────────────────────────────────────────────────────────

app = FastAPI(title="llama.cpp IDE Sidecar (Podman)", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"])

# ── Helpers ────────────────────────────────────────────────────────────────

def require_podman() -> None:
    if not PODMAN_AVAILABLE or _client is None:
        raise HTTPException(503, detail=(
            f"Podman not available (socket: {PODMAN_SOCKET}). "
            "Run `systemctl --user enable --now podman.socket` (Linux) "
            "or `podman machine start` (macOS/Windows)."
        ))

def safe_path(rel_or_abs: str) -> Path:
    p = Path(rel_or_abs)
    if not p.is_absolute():
        p = SANDBOX_ROOT / p
    resolved = p.resolve()
    if not str(resolved).startswith(str(SANDBOX_ROOT)):
        raise HTTPException(403, detail="Access denied: outside sandbox root")
    return resolved

RUNNERS: dict[str, tuple[str, str]] = {
    "python":     ("python3",      ".py"),
    "javascript": ("node",         ".js"),
    "typescript": ("npx ts-node",  ".ts"),
    "bash":       ("bash",         ".sh"),
    "sh":         ("sh",           ".sh"),
    "ruby":       ("ruby",         ".rb"),
    "go":         ("go run",       ".go"),
}

# ══════════════════════════════════════════════════════════════════════════
# Health
# ══════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health() -> dict:
    # Report the default ./models dir so the webui can pre-fill the scanner
    default_models = Path("models")
    default_models_abs = default_models.resolve()
    models_dir_exists = default_models.exists() and default_models.is_dir()
    return {
        "status":             "ok",
        "podman":             PODMAN_AVAILABLE,
        "socket":             PODMAN_SOCKET,
        "sandbox":            str(SANDBOX_ROOT),
        "default_models_dir": str(default_models_abs) if models_dir_exists else None,
        "version":            "0.3.0",
        "ts":                 time.time(),
    }

# ══════════════════════════════════════════════════════════════════════════
# GGUF scan
# ══════════════════════════════════════════════════════════════════════════

class GgufFileInfo(BaseModel):
    path: str; name: str; size_bytes: int; modified_at: str

@app.get("/ide/gguf/scan")
def scan_gguf(
    dir: str = Query(..., description="Directory to scan"),
    max_depth: int = Query(GGUF_MAX_DEPTH, ge=1, le=10),
) -> dict:
    base = safe_path(dir)
    if not base.exists(): raise HTTPException(404, f"Not found: {dir}")
    if not base.is_dir(): raise HTTPException(400, f"Not a directory: {dir}")
    results: list[GgufFileInfo] = []
    def _scan(cur: Path, depth: int) -> None:
        if depth > max_depth: return
        try:
            for entry in sorted(cur.iterdir()):
                if entry.is_symlink(): continue
                if entry.is_dir(): _scan(entry, depth + 1)
                elif entry.is_file() and entry.suffix.lower() == ".gguf":
                    s = entry.stat()
                    results.append(GgufFileInfo(
                        path=str(entry), name=entry.name, size_bytes=s.st_size,
                        modified_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(s.st_mtime)),
                    ))
        except PermissionError: pass
    _scan(base, 1)
    return {"dir": str(base), "count": len(results), "files": [f.model_dump() for f in results]}

# ══════════════════════════════════════════════════════════════════════════
# Container helpers
# ══════════════════════════════════════════════════════════════════════════

class ContainerCreate(BaseModel):
    name: str; image: str
    ports: Optional[str] = None
    mountPath: Optional[str] = None
    env: Optional[str] = None
    cmd: Optional[str] = None

def _c2dict(c) -> dict:
    stats: dict = {}
    if c.status == "running":
        try:
            raw = c.stats(stream=False)
            cpu_d = raw["cpu_stats"]["cpu_usage"]["total_usage"] - raw["precpu_stats"]["cpu_usage"]["total_usage"]
            sys_d = raw["cpu_stats"]["system_cpu_usage"] - raw["precpu_stats"]["system_cpu_usage"]
            n_cpu = raw["cpu_stats"].get("online_cpus", 1)
            stats = {
                "cpuPercent": round((cpu_d / sys_d) * n_cpu * 100 if sys_d > 0 else 0, 2),
                "memoryMB":   round(raw["memory_stats"].get("usage", 0) / (1024 * 1024), 1),
            }
        except Exception: pass
    ports = [f"{b['HostPort']}:{i.split('/')[0]}" for i, bs in (c.ports or {}).items() if bs for b in bs]
    return {"id": c.short_id, "name": c.name,
            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "status": "running" if c.status == "running" else "stopped",
            "ports": ports, **stats}

def _list()   -> list[dict]: require_podman(); return [_c2dict(c) for c in _client.containers.list(all=True)]
def _start(i) -> dict:
    require_podman()
    try: _client.containers.get(i).start(); return {"status": "running"}
    except NotFound: raise HTTPException(404, "Container not found")
def _stop(i)  -> dict:
    require_podman()
    try: _client.containers.get(i).stop(timeout=5); return {"status": "stopped"}
    except NotFound: raise HTTPException(404, "Container not found")
def _remove(i) -> None:
    require_podman()
    try: c = _client.containers.get(i); c.stop(timeout=3); c.remove()
    except NotFound: raise HTTPException(404, "Container not found")
def _create(body: ContainerCreate) -> dict:
    require_podman()
    try: _client.images.get(body.image)
    except Exception: print(f"  Pulling {body.image}…"); _client.images.pull(body.image)
    kw: dict = {"image": body.image, "name": body.name, "detach": True, "tty": True}
    if body.ports:
        h, c_ = body.ports.split(":", 1); kw["ports"] = {f"{c_}/tcp": int(h)}
    if body.mountPath: kw["volumes"] = {body.mountPath: {"bind": "/workspace", "mode": "rw"}}
    if body.env: kw["environment"] = dict(l.split("=", 1) for l in body.env.strip().splitlines() if "=" in l)
    if body.cmd: kw["command"] = body.cmd
    try: c = _client.containers.run(**kw); return {"id": c.short_id, "name": c.name, "status": "running"}
    except APIError as e: raise HTTPException(500, str(e)) from e

# ── Canonical routes: /ide/containers/* ───────────────────────────────────
@app.get("/ide/containers")
def list_containers() -> list[dict]: return _list()
@app.post("/ide/containers", status_code=201)
def create_container(body: ContainerCreate) -> dict: return _create(body)
@app.post("/ide/containers/{i}/start")
def start_container(i: str) -> dict: return _start(i)
@app.post("/ide/containers/{i}/stop")
def stop_container(i: str) -> dict: return _stop(i)
@app.delete("/ide/containers/{i}", status_code=204)
def remove_container(i: str) -> None: _remove(i)

# ── Compat aliases: /ide/docker/* (old frontend store) ────────────────────
@app.get("/ide/docker/containers")
def _lc() -> list[dict]: return _list()
@app.post("/ide/docker/containers", status_code=201)
def _cc(body: ContainerCreate) -> dict: return _create(body)
@app.post("/ide/docker/containers/{i}/start")
def _sc(i: str) -> dict: return _start(i)
@app.post("/ide/docker/containers/{i}/stop")
def _stc(i: str) -> dict: return _stop(i)
@app.delete("/ide/docker/containers/{i}", status_code=204)
def _rc(i: str) -> None: _remove(i)

# ══════════════════════════════════════════════════════════════════════════
# Exec
# ══════════════════════════════════════════════════════════════════════════

class ExecRequest(BaseModel):
    containerId: str; code: str; language: str

class ExecResult(BaseModel):
    stdout: str; stderr: str; exitCode: int; durationMs: float

def _exec(body: ExecRequest) -> ExecResult:
    require_podman()
    lang = body.language.lower()
    ri = RUNNERS.get(lang)
    if not ri: raise HTTPException(400, f"Unsupported language: {lang}")
    runner, ext = ri
    try: c = _client.containers.get(body.containerId)
    except NotFound: raise HTTPException(404, "Container not found")
    if c.status != "running": raise HTTPException(409, "Container not running")
    fname = f"_ide_exec{ext}"
    buf = io.BytesIO(); code_b = body.code.encode()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        info = tarfile.TarInfo(name=fname); info.size = len(code_b); info.mode = 0o644
        tf.addfile(info, io.BytesIO(code_b))
    buf.seek(0); c.put_archive("/tmp", buf)
    t0 = time.perf_counter()
    ec, out = c.exec_run(cmd=["sh", "-c", f"{runner} /tmp/{fname}"], stdout=True, stderr=True, demux=True, workdir="/tmp")
    ms = (time.perf_counter() - t0) * 1000
    ob, eb = out if isinstance(out, tuple) else (out, b"")
    return ExecResult(stdout=(ob or b"").decode(errors="replace"), stderr=(eb or b"").decode(errors="replace"), exitCode=ec or 0, durationMs=round(ms, 1))

@app.post("/ide/containers/exec", response_model=ExecResult)
def exec_c(body: ExecRequest) -> ExecResult: return _exec(body)
@app.post("/ide/docker/exec", response_model=ExecResult)
def exec_c_compat(body: ExecRequest) -> ExecResult: return _exec(body)

# ══════════════════════════════════════════════════════════════════════════
# Host filesystem (sandboxed)
# ══════════════════════════════════════════════════════════════════════════

class FileWrite(BaseModel): content: str

@app.get("/ide/files/{path:path}")
def read_file(path: str) -> dict:
    p = safe_path(path)
    if not p.is_file(): raise HTTPException(404, "Not found")
    return {"path": str(p), "content": p.read_text(encoding="utf-8", errors="replace")}

@app.put("/ide/files/{path:path}")
def write_file(path: str, body: FileWrite) -> dict:
    p = safe_path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body.content, encoding="utf-8"); return {"saved": True, "path": str(p)}

@app.get("/ide/files")
def list_files(dir: str = Query(".")) -> dict:
    d = safe_path(dir)
    if not d.is_dir(): raise HTTPException(404, "Not found")
    entries = []
    for e in sorted(d.iterdir()):
        s = e.stat()
        entries.append({"name": e.name, "path": str(e), "type": "directory" if e.is_dir() else "file",
                        "sizeMB": round(s.st_size/(1024*1024), 2),
                        "modified": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(s.st_mtime))})
    return {"dir": str(d), "entries": entries}

# ══════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("━" * 60)
    print("  llama.cpp IDE Sidecar  v0.3  (Podman)")
    print(f"  Listening : http://{HOST}:{PORT}")
    print(f"  Sandbox   : {SANDBOX_ROOT}")
    print(f"  Podman    : {'connected — ' + PODMAN_SOCKET if PODMAN_AVAILABLE else 'NOT available'}")
    print(f"  Origins   : {', '.join(ORIGINS)}")
    print("━" * 60)
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
