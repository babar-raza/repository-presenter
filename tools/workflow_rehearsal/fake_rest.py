"""An in-process, stateful model of the GitHub REST API the write paths use (TC-REF-11).

``fake_github.py`` answers the act harness from files; this module is the other half the whole-cycle
rehearsal needs: a model that *remembers* what was written, so a second run can be shown to create
nothing, and that can lose a response on demand. It is driven through the same two seams
``core/github/client.py`` and ``core/github/token_provenance.py`` already take (``fetch(url, token)``
and ``write(url, token, payload)``, both returning ``(status, body)``), so the real client, effect
and provenance code runs unchanged against it; only the network is replaced. Nothing here opens a
socket.

What it models, with GitHub's own semantics where the effects depend on them: repositories with a
default branch, branch refs, per-branch files addressed by blob sha (a PUT of an existing file needs
the current sha: 409 when it is stale, 422 when it is missing), pull requests and issues sharing one
number sequence (an issue listing also returns pull requests, flagged ``pull_request``), a pull
request opened by the configured App (``performed_via_github_app``), and the installation token's
repository scope (``/installation/repositories``).

Fault injection (``inject``): ``drop`` (the request never arrives: status -1, nothing applied),
``lose_response`` (the write is applied and the answer is lost: status -1, the realistic timeout
shape that makes reconciliation necessary), ``status`` (an HTTP error, nothing applied, with an
optional ``Retry-After``).

Every request is logged as method, path and the authorization *scheme* only; a token value is never
stored, so a log of this model can be scanned for credentials without a false negative from here.
"""

from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

API_ROOT = "https://api.github.com"
Response = tuple[int, Any]


def _sha(*parts: object) -> str:
    return hashlib.sha1(
        "\0".join(str(p) for p in parts).encode(), usedforsecurity=False
    ).hexdigest()


@dataclass
class _Repo:
    default_branch: str = "main"
    refs: dict[str, str] = field(default_factory=dict)
    files: dict[tuple[str, str], tuple[str, str]] = field(default_factory=dict)
    pulls: list[dict[str, Any]] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    next_number: int = 1
    archived: bool = False
    repository_id: int = 0


@dataclass
class Fault:
    method: str
    pattern: str
    mode: str  # "drop" | "lose_response" | "status"
    status: int = 500
    retry_after: str | None = None
    times: int = 1


class FakeGitHubRest:
    """The stateful REST model. ``fetch`` serves GETs; ``post``/``put``/``patch`` serve writes."""

    def __init__(
        self, *, app_id: int, installation_scope: list[str] | None = None
    ) -> None:
        self.app_id = app_id
        self.installation_scope = list(installation_scope or [])
        self._repos: dict[str, _Repo] = {}
        self._faults: list[Fault] = []
        self.requests: list[dict[str, Any]] = []
        self.writes: list[dict[str, Any]] = []

    # --- setup -------------------------------------------------------------------------------

    def add_repository(
        self,
        repository: str,
        *,
        default_branch: str = "main",
        readme: str | None = None,
        tip: str | None = None,
        repository_id: int = 0,
        files: dict[str, str] | None = None,
    ) -> str:
        """Create ``repository`` with its default branch (and a README when given); return the tip.

        ``tip`` pins the default branch's commit id (a canary rehearsal makes it the local upstream's
        real head); ``files`` adds further files to the default branch."""
        repo = _Repo(default_branch=default_branch, repository_id=repository_id)
        tip = tip or _sha("root", repository)
        repo.refs[default_branch] = tip
        if readme is not None:
            repo.files[(default_branch, "README.md")] = (_sha("blob", readme), readme)
        for path, text in (files or {}).items():
            repo.files[(default_branch, path)] = (_sha("blob", text), text)
        self._repos[repository] = repo
        return tip

    def inject(self, method: str, pattern: str, mode: str, **options: Any) -> None:
        """Make the next ``times`` requests whose method and path match fail as ``mode`` says."""
        self._faults.append(Fault(method.upper(), pattern, mode, **options))

    def set_branch(self, repository: str, branch: str, sha: str) -> None:
        """Record a branch a ``git push`` created or moved (the git side is a local bare remote)."""
        repo = self._repos[repository]
        base = repo.refs.get(repo.default_branch)
        repo.refs[branch] = sha
        for (existing, path), value in list(repo.files.items()):
            if existing == repo.default_branch and base is not None:
                repo.files.setdefault((branch, path), value)

    def set_file(self, repository: str, branch: str, path: str, text: str) -> None:
        """Record a file a ``git push`` changed on ``branch`` (the git side is a local bare remote)."""
        self._repos[repository].files[(branch, path)] = (_sha("blob", text), text)

    def close_pull(self, repository: str, number: int, *, merged: bool = False) -> None:
        for pull in self._repos[repository].pulls:
            if pull["number"] == number:
                pull["state"] = "closed"
                pull["merged_at"] = "2026-10-11T00:00:00Z" if merged else None

    # --- observation (for assertions and evidence) -------------------------------------------

    def pulls(self, repository: str, state: str | None = None) -> list[dict[str, Any]]:
        found = self._repos[repository].pulls
        return [p for p in found if state is None or p["state"] == state]

    def issues(self, repository: str) -> list[dict[str, Any]]:
        return list(self._repos[repository].issues)

    def file(self, repository: str, branch: str, path: str) -> str | None:
        entry = self._repos[repository].files.get((branch, path))
        return entry[1] if entry else None

    def branch(self, repository: str, branch: str) -> str | None:
        return self._repos[repository].refs.get(branch)

    def applied_writes(self) -> list[dict[str, Any]]:
        return [w for w in self.writes if w["applied"]]

    # --- the seams ---------------------------------------------------------------------------

    def fetch(self, url: str, token: str | None) -> Response:
        return self._handle("GET", url, token, None)

    def post(self, url: str, token: str, payload: dict[str, Any]) -> Response:
        return self._handle("POST", url, token, payload)

    def put(self, url: str, token: str, payload: dict[str, Any]) -> Response:
        return self._handle("PUT", url, token, payload)

    def patch(self, url: str, token: str, payload: dict[str, Any]) -> Response:
        return self._handle("PATCH", url, token, payload)

    # --- routing -----------------------------------------------------------------------------

    def _handle(
        self, method: str, url: str, token: str | None, payload: Any
    ) -> Response:
        split = urlsplit(url)
        path = unquote(split.path)
        entry = {"method": method, "path": path, "auth": "bearer" if token else "none"}
        fault = self._take_fault(method, path)
        if fault is not None and fault.mode == "drop":
            self.requests.append({**entry, "status": -1, "fault": "drop"})
            return -1, "ConnectError: injected, the request never arrived"
        if fault is not None and fault.mode == "status":
            self.requests.append({**entry, "status": fault.status, "fault": "status"})
            body: dict[str, Any] = {"message": "injected failure"}
            if fault.retry_after:
                body["retry_after"] = fault.retry_after
            return fault.status, body
        status, body = self._route(method, path, parse_qs(split.query), payload)
        applied = method != "GET" and status < 400
        if method != "GET":
            self.writes.append({**entry, "status": status, "applied": applied})
        if fault is not None and fault.mode == "lose_response":
            self.requests.append({**entry, "status": -1, "fault": "lose_response"})
            return (
                -1,
                "ReadTimeout: injected, the write was applied and the answer was lost",
            )
        self.requests.append({**entry, "status": status})
        return status, body

    def _take_fault(self, method: str, path: str) -> Fault | None:
        for fault in self._faults:
            if (
                fault.times > 0
                and fault.method == method
                and re.search(fault.pattern, path)
            ):
                fault.times -= 1
                return fault
        return None

    def _route(
        self, method: str, path: str, query: dict[str, list[str]], payload: Any
    ) -> Response:
        if method == "GET" and path == "/installation/repositories":
            listed = [{"full_name": name} for name in self.installation_scope]
            return 200, {"total_count": len(listed), "repositories": listed}
        match = re.match(r"^/repos/([^/]+)/([^/]+)(/.*)?$", path)
        if match is None:
            return 404, {"message": "Not Found"}
        repository = f"{match[1]}/{match[2]}"
        repo = self._repos.get(repository)
        if repo is None:
            return 404, {"message": "Not Found"}
        rest = match[3] or ""
        if method == "GET" and rest == "":
            return 200, {
                "id": repo.repository_id,
                "full_name": repository,
                "default_branch": repo.default_branch,
                "archived": repo.archived,
                "visibility": "public",
            }
        tree = re.match(r"^/git/trees/(.+)$", rest)
        if method == "GET" and tree:
            return self._get_tree(repo)
        reference = re.match(r"^/git/ref/heads/(.+)$", rest)
        if method == "GET" and reference:
            sha = repo.refs.get(reference[1])
            return (
                (200, {"object": {"sha": sha}})
                if sha
                else (404, {"message": "Not Found"})
            )
        if method == "POST" and rest == "/git/refs":
            return self._create_ref(repo, payload)
        contents = re.match(r"^/contents/(.+)$", rest)
        if contents and method == "GET":
            return self._get_contents(repo, contents[1], (query.get("ref") or [""])[0])
        if contents and method == "PUT":
            return self._put_contents(repo, contents[1], payload)
        if method == "GET" and rest == "/pulls":
            return 200, self._list_pulls(repository, repo, query)
        if method == "POST" and rest == "/pulls":
            return self._create_pull(repository, repo, payload)
        pull = re.match(r"^/pulls/(\d+)$", rest)
        if pull and method == "PATCH":
            return self._patch_pull(repository, repo, int(pull[1]), payload)
        if pull and method == "GET":
            found = next((p for p in repo.pulls if p["number"] == int(pull[1])), None)
            return (200, self._pull_view(repository, found)) if found else (404, {"message": "Not Found"})
        changed = re.match(r"^/pulls/(\d+)/files$", rest)
        if changed and method == "GET":
            return self._pull_files(repo, int(changed[1]))
        issue = re.match(r"^/issues/(\d+)$", rest)
        if issue and method == "GET":
            return self._get_issue(repo, int(issue[1]))
        if issue and method == "PATCH":
            return self._patch_issue(repo, int(issue[1]), payload)
        if method == "GET" and rest == "/issues":
            return 200, self._list_issues(repository, repo, query)
        if method == "POST" and rest == "/issues":
            return self._create_issue(repository, repo, payload)
        return 404, {"message": f"no route for {method} {path}"}

    # --- handlers ----------------------------------------------------------------------------

    @staticmethod
    def _create_ref(repo: _Repo, payload: dict[str, Any]) -> Response:
        name = str(payload["ref"]).removeprefix("refs/heads/")
        if name in repo.refs:
            return 422, {"message": "Reference already exists"}
        repo.refs[name] = str(payload["sha"])
        # A new branch starts with its base's files, as a git branch does.
        for (branch, path), value in list(repo.files.items()):
            if repo.refs.get(branch) == payload["sha"] and branch != name:
                repo.files[(name, path)] = value
        return 201, {"ref": payload["ref"], "object": {"sha": payload["sha"]}}

    @staticmethod
    def _get_contents(repo: _Repo, path: str, ref: str) -> Response:
        found = repo.files.get((ref or repo.default_branch, path))
        if found is None:
            return 404, {"message": "Not Found"}
        blob, text = found
        content = base64.b64encode(text.encode()).decode()
        return 200, {"sha": blob, "content": content, "encoding": "base64"}

    @staticmethod
    def _put_contents(repo: _Repo, path: str, payload: dict[str, Any]) -> Response:
        branch = str(payload["branch"])
        if branch not in repo.refs:
            return 404, {"message": "Branch not found"}
        current = repo.files.get((branch, path))
        given = payload.get("sha")
        if current is not None and given is None:
            return 422, {"message": "sha wasn't supplied"}
        if current is not None and given != current[0]:
            return 409, {"message": f"{path} does not match {given}"}
        text = base64.b64decode(str(payload["content"])).decode()
        blob = _sha("blob", text)
        commit = _sha("commit", branch, blob, repo.refs[branch], payload.get("message"))
        repo.files[(branch, path)] = (blob, text)
        repo.refs[branch] = commit
        return (200 if current else 201), {
            "content": {"sha": blob},
            "commit": {"sha": commit},
        }

    def _list_pulls(
        self, repository: str, repo: _Repo, query: dict[str, list[str]]
    ) -> list[dict[str, Any]]:
        head = (query.get("head") or [""])[0].split(":", 1)[-1]
        state = (query.get("state") or ["open"])[0]
        matches = [
            p
            for p in repo.pulls
            if (not head or p["head"]["ref"] == head)
            and (state == "all" or p["state"] == state)
        ]
        return [self._pull_view(repository, p) for p in reversed(matches)]

    @staticmethod
    def _pull_view(repository: str, pull: dict[str, Any]) -> dict[str, Any]:
        return {
            **pull,
            "html_url": f"https://github.com/{repository}/pull/{pull['number']}",
        }

    def _create_pull(
        self, repository: str, repo: _Repo, payload: dict[str, Any]
    ) -> Response:
        head = str(payload["head"])
        if head not in repo.refs:
            return 422, {"message": "head branch does not exist"}
        if any(p["state"] == "open" and p["head"]["ref"] == head for p in repo.pulls):
            return 422, {"message": "A pull request already exists for this head"}
        number = repo.next_number
        repo.next_number += 1
        pull = {
            "number": number,
            "state": "open",
            "merged_at": None,
            "title": payload["title"],
            "body": payload.get("body") or "",
            "head": {"ref": head, "repo": {"full_name": repository}},
            "base": {"ref": payload["base"]},
            "user": {"login": "repository-presenter[bot]", "type": "Bot"},
            "performed_via_github_app": {"id": self.app_id},
        }
        repo.pulls.append(pull)
        return 201, self._pull_view(repository, pull)

    @staticmethod
    def _get_tree(repo: _Repo) -> Response:
        names = sorted({path.split("/", 1)[0] for (branch, path) in repo.files if branch == repo.default_branch})
        return 200, {
            "truncated": False,
            "tree": [
                {"path": n, "type": "tree" if any(p.startswith(n + "/") for (b, p) in repo.files if b == repo.default_branch) else "blob"}
                for n in names
            ],
        }

    @staticmethod
    def _pull_files(repo: _Repo, number: int) -> Response:
        pull = next((p for p in repo.pulls if p["number"] == number), None)
        if pull is None:
            return 404, {"message": "Not Found"}
        head, base = pull["head"]["ref"], pull["base"]["ref"]
        files = []
        for (branch, path), (blob, _text) in sorted(repo.files.items()):
            if branch != head:
                continue
            before = repo.files.get((base, path))
            if before is None or before[0] != blob:
                files.append({"filename": path, "status": "added" if before is None else "modified"})
        return 200, files

    def _patch_pull(
        self, repository: str, repo: _Repo, number: int, payload: dict[str, Any]
    ) -> Response:
        for pull in repo.pulls:
            if pull["number"] == number:
                pull.update({k: payload[k] for k in ("title", "body") if k in payload})
                return 200, self._pull_view(repository, pull)
        return 404, {"message": "Not Found"}

    def _get_issue(self, repo: _Repo, number: int) -> Response:
        for item in [*repo.issues, *repo.pulls]:
            if item["number"] == number:
                return 200, {
                    "number": number,
                    "state": item["state"],
                    "title": item["title"],
                    "body": item["body"],
                    "performed_via_github_app": item.get("performed_via_github_app"),
                }
        return 404, {"message": "Not Found"}

    @staticmethod
    def _patch_issue(repo: _Repo, number: int, payload: dict[str, Any]) -> Response:
        for issue in repo.issues:
            if issue["number"] == number:
                issue["state"] = payload.get("state", issue["state"])
                return 200, dict(issue)
        return 404, {"message": "Not Found"}

    def _list_issues(
        self, repository: str, repo: _Repo, query: dict[str, list[str]]
    ) -> list[dict[str, Any]]:
        state = (query.get("state") or ["open"])[0]
        every = [*repo.issues, *({**p, "pull_request": {}} for p in repo.pulls)]
        return [
            {
                **item,
                "html_url": f"https://github.com/{repository}/issues/{item['number']}",
            }
            for item in sorted(every, key=lambda i: -i["number"])
            if state == "all" or item["state"] == state
        ]

    def _create_issue(
        self, repository: str, repo: _Repo, payload: dict[str, Any]
    ) -> Response:
        number = repo.next_number
        repo.next_number += 1
        issue = {
            "number": number,
            "state": "open",
            "title": payload["title"],
            "body": payload.get("body") or "",
            "performed_via_github_app": {"id": self.app_id},
        }
        repo.issues.append(issue)
        return 201, {
            **issue,
            "html_url": f"https://github.com/{repository}/issues/{number}",
        }
