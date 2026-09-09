#!/usr/bin/env python3
"""Refresh exact manifest snapshots for Amplifier Smart Tools without checking out upstream code."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit


DEFAULT_TIMEOUT_SECONDS = 30
MAXIMUM_TIMEOUT_SECONDS = 120
ALLOWED_SOURCE_FIELDS = {"repository", "ref", "path"}
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")


class RefreshError(Exception):
    """A source entry could not be refreshed safely."""


class GitError(RefreshError):
    """A Git operation failed without exposing upstream output."""


class OutputError(RefreshError):
    """A local snapshot output failure requires a non-committing exit."""


@dataclass(frozen=True)
class Source:
    repository: str
    ref: str
    path: str


@dataclass(frozen=True)
class PreparedSnapshot:
    manifest: bytes
    provenance: bytes


def parse_source(source_file: Path) -> Source:
    """Load and validate one catalog source pointer."""
    if source_file.is_symlink() or source_file.parent.is_symlink():
        raise RefreshError("source.json and its entry directory must not be symlinks")
    try:
        value = json.loads(source_file.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RefreshError("source.json is not valid UTF-8 JSON") from error

    if not isinstance(value, dict) or set(value) - ALLOWED_SOURCE_FIELDS:
        raise RefreshError("source.json must contain only repository, ref, and path fields")

    repository = required_string(value, "repository")
    validate_repository(repository)
    ref = value.get("ref", "main")
    path = value.get("path", ".")
    validate_ref(ref)
    validate_relative_path(path, "distribution path")
    return Source(repository=repository, ref=ref, path=path)


def required_string(value: dict[str, Any], field: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item:
        raise RefreshError(f"{field} must be a nonempty string")
    return item


def validate_repository(repository: str) -> None:
    """Accept only credential-free HTTPS Git URLs."""
    if any(ord(character) <= 32 for character in repository):
        raise RefreshError("repository must be a valid HTTPS Git URL")
    try:
        parsed = urlsplit(repository)
        hostname = parsed.hostname
        parsed.port
    except ValueError as error:
        raise RefreshError("repository must be a valid HTTPS Git URL") from error
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not parsed.path
    ):
        raise RefreshError("repository must be a credential-free HTTPS Git URL")


def validate_ref(ref: Any) -> None:
    if not isinstance(ref, str) or not ref:
        raise RefreshError("ref must be a nonempty string")
    forbidden = set(" ~^:?*[\\")
    if (
        ref.startswith("-")
        or ref.startswith("/")
        or ref.endswith("/")
        or ref == "@"
        or "//" in ref
        or ".." in ref
        or "@{" in ref
        or any(character in forbidden or ord(character) < 32 for character in ref)
        or any(
            component.startswith(".") or component.endswith(".lock")
            for component in ref.split("/")
        )
    ):
        raise RefreshError("ref is not a safe Git ref")


def validate_relative_path(path: Any, label: str) -> tuple[str, ...]:
    if not isinstance(path, str) or not path:
        raise RefreshError(f"{label} must be a nonempty string")
    if path == ".":
        return ()
    if (
        "\\" in path
        or path.startswith("/")
        or "//" in path
        or any(ord(character) < 32 for character in path)
    ):
        raise RefreshError(f"{label} must be a safe relative POSIX path")
    parts = PurePosixPath(path).parts
    if not parts or any(part in {".", ".."} for part in parts):
        raise RefreshError(f"{label} must be a safe relative POSIX path")
    return parts


def git_environment(home: Path) -> dict[str, str]:
    """Return a minimal, non-interactive Git environment for upstream reads."""
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "config"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_COUNT": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ALLOW_PROTOCOL": "https",
    }


def run_git(
    arguments: list[str], *, cwd: Path, env: dict[str, str], timeout: int, purpose: str
) -> bytes:
    """Run Git without forwarding its output, which can contain upstream content."""
    try:
        completed = subprocess.run(
            ["git", "-c", "credential.helper=", *arguments],
            cwd=cwd,
            env=env,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise GitError(f"{purpose} failed") from error
    if completed.returncode:
        raise GitError(f"{purpose} failed")
    return completed.stdout


class RepositoryCache:
    """Resolve each repository/ref once in a temporary bare repository."""

    def __init__(self, temporary_root: Path, timeout: int) -> None:
        self.temporary_root = temporary_root
        self.timeout = timeout
        self.environment = git_environment(temporary_root / "home")
        (temporary_root / "home" / "config").mkdir(parents=True)
        self._resolved: dict[tuple[str, str], tuple[Path, str]] = {}
        self._failures: dict[tuple[str, str], RefreshError] = {}

    def resolve(self, source: Source) -> tuple[Path, str]:
        key = (source.repository, source.ref)
        if key in self._resolved:
            return self._resolved[key]
        if key in self._failures:
            raise self._failures[key]

        bare_repository = self.temporary_root / (
            f"source-{len(self._resolved) + len(self._failures)}.git"
        )
        try:
            run_git(
                ["init", "--bare", str(bare_repository)],
                cwd=self.temporary_root,
                env=self.environment,
                timeout=self.timeout,
                purpose="temporary repository initialization",
            )
            run_git(
                ["remote", "add", "origin", source.repository],
                cwd=bare_repository,
                env=self.environment,
                timeout=self.timeout,
                purpose="source remote setup",
            )
            run_git(
                ["fetch", "--no-tags", "--depth=1", "origin", source.ref],
                cwd=bare_repository,
                env=self.environment,
                timeout=self.timeout,
                purpose="requested ref fetch",
            )
            commit = run_git(
                ["rev-parse", "--verify", "FETCH_HEAD^{commit}"],
                cwd=bare_repository,
                env=self.environment,
                timeout=self.timeout,
                purpose="requested ref resolution",
            ).decode("ascii", "strict").strip().lower()
            if not COMMIT_PATTERN.fullmatch(commit):
                raise GitError("requested ref resolution failed")
        except RefreshError as error:
            self._failures[key] = error
            raise
        self._resolved[key] = (bare_repository, commit)
        return self._resolved[key]


def object_type(
    repository: Path, commit: str, path: str, cache: RepositoryCache, purpose: str
) -> str:
    revision = f"{commit}^{'{tree}'}" if path == "." else f"{commit}:{path}"
    return run_git(
        ["cat-file", "-t", revision],
        cwd=repository,
        env=cache.environment,
        timeout=cache.timeout,
        purpose=purpose,
    ).decode("ascii", "strict").strip()


def validate_repository_file(
    repository: Path, commit: str, file_path: str, cache: RepositoryCache
) -> None:
    """Reject symlink traversal before reading a repository file."""
    parts = validate_relative_path(file_path, "repository file path")
    if not parts:
        raise RefreshError("repository file path must name a file")

    for position in range(1, len(parts)):
        parent = "/".join(parts[:position])
        if object_type(repository, commit, parent, cache, "repository path validation") != "tree":
            raise RefreshError("repository path contains a symlink or non-directory")

    listing = run_git(
        ["ls-tree", "-z", commit, "--", file_path],
        cwd=repository,
        env=cache.environment,
        timeout=cache.timeout,
        purpose="repository file validation",
    )
    if not listing:
        raise RefreshError("repository file is missing")
    metadata, separator, _name = listing.partition(b"\t")
    if not separator or metadata.split(b" ", 1)[0] == b"120000":
        raise RefreshError("repository file must not be a symlink")
    if object_type(repository, commit, file_path, cache, "repository file validation") != "blob":
        raise RefreshError("repository file must be a regular file")


def read_repository_file(
    repository: Path, commit: str, file_path: str, cache: RepositoryCache
) -> bytes:
    validate_repository_file(repository, commit, file_path, cache)
    return run_git(
        ["show", f"{commit}:{file_path}"],
        cwd=repository,
        env=cache.environment,
        timeout=cache.timeout,
        purpose="repository file read",
    )


def join_repository_path(*path_groups: tuple[str, ...]) -> str:
    parts = tuple(part for group in path_groups for part in group)
    return "/".join(parts)


def prepare_snapshot(source: Source, cache: RepositoryCache) -> PreparedSnapshot:
    repository, commit = cache.resolve(source)
    distribution_parts = validate_relative_path(source.path, "distribution path")
    if distribution_parts and object_type(
        repository, commit, "/".join(distribution_parts), cache, "distribution path validation"
    ) != "tree":
        raise RefreshError("distribution path contains a symlink or is not a directory")

    descriptor_path = join_repository_path(distribution_parts, ("smart-tool.json",))
    descriptor_bytes = read_repository_file(repository, commit, descriptor_path, cache)
    try:
        descriptor = json.loads(descriptor_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RefreshError("smart-tool.json is not valid UTF-8 JSON") from error
    if not isinstance(descriptor, dict):
        raise RefreshError("smart-tool.json must contain an object")
    manifest_path = required_string(descriptor, "manifest")
    manifest_parts = validate_relative_path(manifest_path, "manifest path")
    if not manifest_parts or manifest_parts[-1] != "SMART_TOOL.md":
        raise RefreshError("manifest path must name SMART_TOOL.md")
    original_manifest_path = join_repository_path(distribution_parts, manifest_parts)
    manifest = read_repository_file(repository, commit, original_manifest_path, cache)
    if not manifest:
        raise RefreshError("SMART_TOOL.md must be nonempty")
    try:
        manifest.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RefreshError("SMART_TOOL.md must be UTF-8 text") from error

    provenance = {
        "source": {
            "repository": source.repository,
            "ref": source.ref,
            "path": source.path,
            "commit": commit,
        },
        "original_manifest_path": original_manifest_path,
        "last_success": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    return PreparedSnapshot(
        manifest=manifest,
        provenance=(json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def replace_pair(entry_directory: Path, prepared: PreparedSnapshot) -> None:
    """Stage both outputs before replacing either existing snapshot file.

    A replacement failure is fatal: callers must not commit a potentially
    partial pair. Existing source failures never reach this function.
    """
    staged: list[tuple[Path, Path]] = []
    try:
        for filename, content in (
            ("SMART_TOOL.md", prepared.manifest),
            ("provenance.json", prepared.provenance),
        ):
            descriptor, temporary_name = tempfile.mkstemp(prefix=f".{filename}.", dir=entry_directory)
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "wb") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            staged.append((temporary_path, entry_directory / filename))
        for temporary_path, target in staged:
            os.replace(temporary_path, target)
    except OSError as error:
        raise OutputError("snapshot output failed") from error
    finally:
        for temporary_path, _target in staged:
            temporary_path.unlink(missing_ok=True)


def entry_files(catalog_root: Path) -> list[Path]:
    tools_directory = catalog_root / "tools"
    if not tools_directory.is_dir() or tools_directory.is_symlink():
        raise RefreshError("catalog tools directory is missing or unsafe")
    return sorted(tools_directory.glob("*/source.json"))


def refresh(catalog_root: Path, timeout: int) -> int:
    errors = 0
    try:
        sources = entry_files(catalog_root)
    except RefreshError as error:
        print(f"ERROR catalog: {error}", file=sys.stderr)
        return 1

    try:
        with tempfile.TemporaryDirectory(prefix="smart-tool-refresh-") as temporary_name:
            cache = RepositoryCache(Path(temporary_name), timeout)
            for source_file in sources:
                slug = source_file.parent.name
                try:
                    source = parse_source(source_file)
                    prepared = prepare_snapshot(source, cache)
                    replace_pair(source_file.parent, prepared)
                except OutputError as error:
                    print(f"FATAL {slug}: {error}", file=sys.stderr)
                    return 2
                except RefreshError as error:
                    errors += 1
                    print(f"ERROR {slug}: {error}", file=sys.stderr)
                else:
                    print(f"OK {slug}: refreshed")
    except OSError:
        print("FATAL catalog: temporary workspace failed", file=sys.stderr)
        return 2
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh exact manifest snapshots for Amplifier Smart Tools from HTTPS Git sources."
    )
    parser.add_argument(
        "--catalog-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="catalog root containing tools/",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="maximum seconds per Git subprocess",
    )
    arguments = parser.parse_args()
    if not 0 < arguments.timeout <= MAXIMUM_TIMEOUT_SECONDS:
        parser.error(f"--timeout must be between 1 and {MAXIMUM_TIMEOUT_SECONDS} seconds")
    return refresh(arguments.catalog_root.resolve(), arguments.timeout)


if __name__ == "__main__":
    raise SystemExit(main())