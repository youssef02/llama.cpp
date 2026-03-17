# IDE Sidecar

Bridges the webui IDE and Model Manager to Podman + local filesystem.

## Quick start

```bash
# 1. Install
pip install fastapi uvicorn docker

# 2. Enable Podman socket
systemctl --user enable --now podman.socket   # Linux
# or: podman machine start                    # macOS / Windows

# 3. Run (from the llama.cpp root)
python tools/server/ide-sidecar/main.py
```

Listens on **:8081**. The Vite dev server already proxies `/ide → :8081` (see `webui/vite.config.ts`).

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `PODMAN_SOCKET` | auto-detected | Override the Podman socket path |
| `IDE_SIDECAR_HOST` | `0.0.0.0` | Bind address |
| `IDE_SIDECAR_PORT` | `8081` | Port |
| `IDE_SIDECAR_ROOT` | `cwd` | Sandbox root for file access |
| `IDE_SIDECAR_GGUF_MAX_DEPTH` | `4` | Max recursion depth for GGUF scan |
| `IDE_SIDECAR_ORIGINS` | localhost:5173,8080 | CORS origins |

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Status + Podman availability |
| GET | `/ide/gguf/scan?dir=...` | Scan directory for .gguf files |
| GET | `/ide/containers` | List Podman containers |
| POST | `/ide/containers` | Create + start a container |
| POST | `/ide/containers/:id/start` | Start |
| POST | `/ide/containers/:id/stop` | Stop |
| DELETE | `/ide/containers/:id` | Remove |
| POST | `/ide/containers/exec` | Execute code inside container |
| GET | `/ide/files?dir=...` | List files (sandboxed) |
| GET | `/ide/files/:path` | Read file |
| PUT | `/ide/files/:path` | Write file |

## Production proxy

For the built binary (llama-server serves `index.html.gz` directly), add a reverse proxy:

**nginx:**
```nginx
location /ide/ { proxy_pass http://localhost:8081/ide/; }
location /     { proxy_pass http://localhost:8080/; }
```

**Caddy:**
```
localhost {
    reverse_proxy /ide/* localhost:8081
    reverse_proxy /* localhost:8080
}
```
