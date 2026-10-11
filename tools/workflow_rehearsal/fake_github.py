"""A local stand-in for the GitHub services a workflow talks to (TC-REF-10-02).

One stdlib-only HTTPS server that answers, from a "world" directory of synthetic bare repositories
(``scenarios.py``), the endpoints this project's workflows use:

- REST (``api.github.com``): ``/repos/{o}/{r}``, ``/commits/{branch}``, ``/git/trees/{sha}``,
  ``/contents/{path}``, App installation lookup (``/repos/{o}/{r}/installation``,
  ``/orgs/{o}/installation``), ``POST /app/installations/{id}/access_tokens`` (a FAKE token),
  ``DELETE /installation/token``, and a recording store for pull requests and issues.
- Git smart HTTP (``git.rehearsal.local``), through ``git http-backend``: read-only
  (``upload-pack``); a push is refused unless the world opts a repository in.

Every request is appended to ``<world>/requests.jsonl`` with the method, path, status and the
authorization scheme only (never a value). A mutating request to anything other than the token
endpoints is also recorded in ``<world>/writes.jsonl``: the rehearsal's proof that a write reached a
fake and nothing else. No real credential is accepted, needed or stored: tokens are the literal
``FAKE_REHEARSAL_INSTALLATION_TOKEN``.

``world.json`` keys: ``archived`` / ``deleted`` (repository names), ``heads`` (name -> sha override),
``failures`` (name -> HTTP status to inject, with an optional ``Retry-After``).

Run (inside the harness's container): ``python3 fake_github.py --world /world --cert tls/server.pem
--key tls/server.key --port 443``. It uses only the standard library so it runs on the CI image's
system python.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

FAKE_TOKEN = "FAKE_REHEARSAL_INSTALLATION_TOKEN"
INSTALLATION_ID = 424242
_LOCK = threading.Lock()
_GIT_PATH = re.compile(r"^/(?P<owner>[^/]+)/(?P<name>[^/]+?)\.git/(?P<rest>.*)$")


def _git(args: list[str], cwd: Path) -> str | None:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


class World:
    """The synthetic upstream state one rehearsal serves."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.meta: dict[str, Any] = {}
        meta_path = root / "world.json"
        if meta_path.is_file():
            self.meta = json.loads(meta_path.read_text(encoding="utf-8"))

    def bare(self, repository: str) -> Path | None:
        owner, _, name = repository.partition("/")
        path = self.root / "upstreams" / owner / f"{name}.git"
        return path if path.is_dir() else None

    def injected(self, repository: str) -> dict[str, Any] | None:
        return (self.meta.get("failures") or {}).get(repository)

    def deleted(self, repository: str) -> bool:
        return repository in (self.meta.get("deleted") or [])

    def default_branch(self, repository: str) -> str:
        bare = self.bare(repository)
        head = _git(["symbolic-ref", "--short", "HEAD"], bare) if bare else None
        return head or "main"

    def head(self, repository: str) -> str:
        override = (self.meta.get("heads") or {}).get(repository)
        if override:
            return str(override)
        bare = self.bare(repository)
        sha = _git(["rev-parse", "HEAD"], bare) if bare else None
        # A repository nobody built a history for still answers, deterministically.
        return sha or hashlib.sha1(f"rehearsal:{repository}".encode()).hexdigest()  # noqa: S324

    def tree(self, repository: str, sha: str) -> list[dict[str, str]] | None:
        bare = self.bare(repository)
        if bare is None:
            return [{"path": "README.md", "mode": "100644", "type": "blob", "sha": self.head(repository)}]
        listing = _git(["ls-tree", "-r", sha], bare)
        if listing is None:
            return None
        entries = []
        for line in listing.splitlines():
            meta, _, path = line.partition("\t")
            mode, kind, object_id = meta.split()
            entries.append({"path": path, "mode": mode, "type": kind, "sha": object_id})
        return entries

    def file(self, repository: str, path: str, ref: str) -> bytes | None:
        bare = self.bare(repository)
        if bare is None:
            return None
        result = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=bare, capture_output=True, check=False)
        return result.stdout if result.returncode == 0 else None


def route(world: World, method: str, path: str, query: dict[str, list[str]], body: bytes) -> tuple[int, Any, dict[str, str]]:
    """Pure routing: ``(status, JSON body, extra headers)``. No I/O beyond the world's git reads."""
    parts = [p for p in path.split("/") if p]
    headers: dict[str, str] = {}
    if method == "POST" and parts[:2] == ["app", "installations"] and parts[-1:] == ["access_tokens"]:
        payload = json.loads(body or b"{}")
        return 201, {
            "token": FAKE_TOKEN,
            "expires_at": "2099-01-01T00:00:00Z",
            "permissions": payload.get("permissions", {}),
            "repository_selection": "selected",
        }, headers
    if method == "DELETE" and parts == ["installation", "token"]:
        return 204, None, headers
    if method == "GET" and (
        (len(parts) == 4 and parts[0] == "repos" and parts[3] == "installation")
        or (len(parts) == 3 and parts[0] in ("orgs", "users") and parts[2] == "installation")
    ):
        return 200, {"id": INSTALLATION_ID, "account": {"login": parts[1]}}, headers
    if len(parts) >= 3 and parts[0] == "repos":
        repository = f"{parts[1]}/{parts[2]}"
        injected = world.injected(repository)
        if injected:
            if injected.get("retry_after"):
                headers["Retry-After"] = str(injected["retry_after"])
            return int(injected["status"]), {"message": "injected failure"}, headers
        if world.deleted(repository):
            return 404, {"message": "Not Found"}, headers
        rest = parts[3:]
        if method == "GET" and not rest:
            return 200, {
                "full_name": repository,
                "default_branch": world.default_branch(repository),
                "archived": repository in (world.meta.get("archived") or []),
            }, headers
        if method == "GET" and rest[:1] == ["commits"] and len(rest) == 2:
            return 200, {"sha": world.head(repository)}, headers
        if method == "GET" and rest[:2] == ["git", "trees"] and len(rest) == 3:
            entries = world.tree(repository, rest[2])
            if entries is None:
                return 404, {"message": "Not Found"}, headers
            return 200, {"sha": rest[2], "tree": entries, "truncated": False}, headers
        if method == "GET" and rest[:1] == ["contents"]:
            ref = (query.get("ref") or [world.default_branch(repository)])[0]
            content = world.file(repository, "/".join(rest[1:]), ref)
            if content is None:
                return 404, {"message": "Not Found"}, headers
            return 200, {"encoding": "base64", "content": base64.b64encode(content).decode()}, headers
        if method == "POST" and rest in (["pulls"], ["issues"]):
            payload = json.loads(body or b"{}")
            number = 1 + len(_read_lines(world.root / "writes.jsonl"))
            return 201, {"number": number, "html_url": f"https://github.com/{repository}/{rest[0]}/{number}", **payload}, headers
        if method == "GET" and rest in (["pulls"], ["issues"]):
            return 200, [], headers
    return 404, {"message": f"fake github: no route for {method} {path}"}, headers


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []


class Handler(BaseHTTPRequestHandler):
    world: World
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        pass

    def _record(self, status: int, host_kind: str) -> None:
        auth = self.headers.get("Authorization", "")
        scheme = auth.split(" ", 1)[0].lower() if auth else "none"
        entry = {"method": self.command, "path": self.path.split("?")[0], "status": status, "kind": host_kind, "auth": scheme}
        with _LOCK:
            with (self.world.root / "requests.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            token_endpoint = "/access_tokens" in self.path or self.path.endswith("/installation/token")
            if self.command not in ("GET", "HEAD") and not token_endpoint and host_kind == "rest":
                with (self.world.root / "writes.jsonl").open("a", encoding="utf-8") as f:
                    f.write(json.dumps({**entry, "to": "fake"}) + "\n")

    def _send(self, status: int, payload: Any, headers: dict[str, str] | None = None) -> None:
        raw = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def _handle(self) -> None:
        split = urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        if _GIT_PATH.match(split.path):
            self._git(split, body)
            return
        status, payload, headers = route(self.world, self.command, split.path, parse_qs(split.query), body)
        self._record(status, "rest")
        self._send(status, payload, headers)

    def _git(self, split: Any, body: bytes) -> None:
        match = _GIT_PATH.match(split.path)
        assert match is not None
        repository = f"{match['owner']}/{match['name']}"
        # Read-only by default: a push endpoint is refused unless the world opts the repository in.
        pushing = "git-receive-pack" in split.path or "service=git-receive-pack" in split.query
        if pushing and repository not in (self.world.meta.get("pushable") or []):
            self._record(403, "git")
            self._send(403, {"message": "fake github: push refused (read-only upstream)"})
            return
        if self.world.deleted(repository) or self.world.bare(repository) is None:
            self._record(404, "git")
            self._send(404, {"message": "Not Found"})
            return
        env = {
            **os.environ,
            "GIT_PROJECT_ROOT": str(self.world.root / "upstreams"),
            "GIT_HTTP_EXPORT_ALL": "1",
            "PATH_INFO": split.path,
            "QUERY_STRING": split.query,
            "REQUEST_METHOD": self.command,
            "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            "CONTENT_LENGTH": str(len(body)),
            "REMOTE_USER": "rehearsal",
            "REMOTE_ADDR": "127.0.0.1",
        }
        if self.headers.get("Content-Encoding"):
            env["HTTP_CONTENT_ENCODING"] = self.headers["Content-Encoding"]
        result = subprocess.run(["git", "http-backend"], input=body, env=env, capture_output=True, check=False)
        head, _, payload = result.stdout.partition(b"\r\n\r\n")
        status, out_headers = 200, []
        for line in head.decode("latin-1").splitlines():
            key, _, value = line.partition(":")
            if key.lower() == "status":
                status = int(value.strip().split()[0])
            elif key.lower() not in ("content-length",):
                out_headers.append((key, value.strip()))
        self._record(status, "git")
        self.send_response(status)
        for key, value in out_headers:
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = do_DELETE = do_PUT = do_PATCH = do_HEAD = _handle


def serve(world_root: Path, *, host: str, port: int, cert: Path | None, key: Path | None) -> ThreadingHTTPServer:
    """Build (not start) the server; TLS when ``cert`` and ``key`` are given."""
    Handler.world = World(world_root)
    server = ThreadingHTTPServer((host, port), Handler)
    if cert and key:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(cert), str(key))
        server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")  # noqa: S104 - inside the rehearsal network
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--cert", type=Path)
    parser.add_argument("--key", type=Path)
    args = parser.parse_args(argv)
    server = serve(args.world, host=args.host, port=args.port, cert=args.cert, key=args.key)
    print(f"fake github serving {args.world} on {args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
