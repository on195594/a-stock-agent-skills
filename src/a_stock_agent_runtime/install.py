"""Reversible, standard-library installer for the portable Skill suite."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib


CLIENT_ROOTS = {
    "claude": (".claude", "skills"),
    "codex": (".agents", "skills"),
    "hermes": (".hermes", "skills", "research"),
}
SKILLS = ("a-stock-research", "a-stock-monitor", "a-stock-qa")
CONSOLE_SCRIPTS = ("a-stock-cache", "a-stock-fetch", "a-stock-install")
REQUIRED_A_STOCK_LIB_VERSION = "0.5.2"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if item.is_file() and ".git" not in item.parts:
            digest.update(str(item.relative_to(path)).encode())
            digest.update(_sha256(item).encode())
    return digest.hexdigest()


def _release(source: Path) -> str:
    data = tomllib.loads((source / "pyproject.toml").read_text(encoding="utf-8"))
    version = str(data["project"]["version"])
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "--short=12", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "working-tree"
    return f"{version}-{commit}"


def _git_commit(path: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _build_lib_wheel(source: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    uv = shutil.which("uv")
    if uv:
        command = [uv, "build", str(source), "--out-dir", str(destination)]
    else:
        source_python = source / ".venv" / "bin" / "python"
        if source_python.is_file():
            command = [str(source_python), "-m", "build", str(source), "--wheel", "--outdir", str(destination)]
        else:
            command = []
    if command:
        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except (OSError, subprocess.CalledProcessError):
            # A checked-in/generated dist wheel is an explicit source checkout
            # fallback when bootstrap networking is unavailable.
            pass
    wheels = sorted(destination.glob("a_stock_lib-*.whl"))
    if not wheels:
        wheels = sorted((source / "dist").glob("a_stock_lib-*.whl"))
    if not wheels:
        raise RuntimeError("a-stock-lib source did not produce a wheel")
    return wheels[-1]


def _build_suite_wheel(source: Path, destination: Path) -> Path:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required for immutable runtime installation")
    build_source = destination / "source"
    build_source.mkdir()
    shutil.copy2(source / "pyproject.toml", build_source)
    shutil.copytree(source / "src", build_source / "src")
    subprocess.run(
        [uv, "build", str(build_source), "--wheel", "--out-dir", str(destination)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    wheels = sorted(destination.glob("a_stock_agent_skills-*.whl"))
    if not wheels:
        raise RuntimeError("suite source did not produce a wheel")
    return wheels[-1]


def _target(root: Path, client: str, skill: str) -> Path:
    return root.joinpath(*CLIENT_ROOTS[client], skill)


def _backup(path: Path, root: Path) -> Path:
    backup_root = root / ".local" / "share" / "a-stock-agent" / "backups"
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = backup_root / f"{path.name}-{time.time_ns()}"
    if path.is_symlink():
        destination.write_text(os.readlink(path), encoding="utf-8")
    elif path.is_dir():
        shutil.copytree(path, destination, symlinks=True)
    else:
        shutil.copy2(path, destination)
    return destination


def _install_runtime(
    source: Path, root: Path, lib_source: Path | None, lib_wheel: Path | None,
    suite_wheel: Path,
) -> tuple[Path, str]:
    release = _release(source)
    runtime_root = root / ".local" / "share" / "a-stock-agent" / "runtime" / release
    venv = runtime_root / "venv"
    runtime_root.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    subprocess.run(
        [sys.executable, "-m", "venv", "--system-site-packages", str(venv)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    python = venv / "bin" / "python"
    wheel = lib_wheel
    wheel_hash = ""
    wheel_display = ""
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    try:
        if lib_source is not None:
            temp_dir = tempfile.TemporaryDirectory(prefix="a-stock-lib-wheel-")
            wheel = _build_lib_wheel(lib_source, Path(temp_dir.name))
        if wheel is None:
            raise ValueError("one of --a-stock-lib-source or --a-stock-lib-wheel is required")
        lib_version = wheel.name.split("-", 2)[1].replace("_", "-")
        if lib_version != REQUIRED_A_STOCK_LIB_VERSION:
            raise RuntimeError(
                f"a-stock-lib version mismatch: expected {REQUIRED_A_STOCK_LIB_VERSION}, got {lib_version}"
            )
        wheel_hash = _sha256(wheel)
        wheel_display = str(wheel)
        installer = shutil.which("uv")
        if installer is None:
            raise RuntimeError("uv is required for immutable runtime installation")
        install_cmd = [
            installer, "pip", "install", "--python", str(python),
            "--no-deps", "--force-reinstall",
        ]
        subprocess.run([*install_cmd, str(wheel)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        subprocess.run([*install_cmd, str(suite_wheel)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()
    installed = subprocess.check_output(
        [str(python), "-c", "import importlib.metadata as m; print(m.version('a-stock-lib'))"],
        text=True,
    ).strip()
    if installed != lib_version:
        raise RuntimeError(f"a-stock-lib version mismatch: expected {lib_version}, got {installed}")
    metadata = {
        "name": "a-stock-lib",
        "version": lib_version,
        "source_commit": _git_commit(lib_source) if lib_source else "wheel-input",
        "wheel": wheel_display,
        "wheel_sha256": wheel_hash,
    }
    (runtime_root / "a-stock-lib-install.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    bin_dir = root / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in CONSOLE_SCRIPTS:
        command = venv / "bin" / name
        link = bin_dir / name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(command)
    return venv, release


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the portable A-stock Skills suite")
    parser.add_argument("--client", choices=[*CLIENT_ROOTS, "all"], default="all")
    parser.add_argument("--mode", choices=("symlink", "copy"), default="symlink")
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument("--target-root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--a-stock-lib-source", type=Path)
    parser.add_argument("--a-stock-lib-wheel", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    source = args.source.expanduser().resolve()
    root = (args.target_root or Path.home()).expanduser().resolve()
    if not (source / "pyproject.toml").is_file():
        print(f"source is not a canonical suite: {source}", file=sys.stderr)
        return 2
    if bool(args.a_stock_lib_source) == bool(args.a_stock_lib_wheel):
        print("exactly one of --a-stock-lib-source or --a-stock-lib-wheel is required", file=sys.stderr)
        return 2
    lib_source = args.a_stock_lib_source.expanduser().resolve() if args.a_stock_lib_source else None
    lib_wheel = args.a_stock_lib_wheel.expanduser().resolve() if args.a_stock_lib_wheel else None
    if lib_source and not (lib_source / "pyproject.toml").is_file():
        print(f"invalid a-stock-lib source: {lib_source}", file=sys.stderr)
        return 2
    if lib_wheel and (not lib_wheel.is_file() or lib_wheel.suffix != ".whl"):
        print(f"invalid a-stock-lib wheel: {lib_wheel}", file=sys.stderr)
        return 2
    if shutil.which("uv") is None:
        print("uv is required for immutable runtime installation", file=sys.stderr)
        return 2
    clients = list(CLIENT_ROOTS) if args.client == "all" else [args.client]
    if root.joinpath(".local", "bin").as_posix() not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"PATH must contain {root / '.local' / 'bin'} for stable CLI discovery", file=sys.stderr)
        return 2
    release = _release(source)
    print(json.dumps({"source": str(source), "release": release, "clients": clients, "mode": args.mode}, ensure_ascii=False))
    if args.dry_run:
        for client in clients:
            for skill in SKILLS:
                print(f"DRY-RUN {args.mode} {source / 'skills' / skill} -> {_target(root, client, skill)}")
        print(f"DRY-RUN runtime -> {root / '.local/share/a-stock-agent/runtime' / release / 'venv'}")
        return 0
    targets = [
        (source / "skills" / skill, _target(root, client, skill))
        for client in clients for skill in SKILLS
    ]
    for source_skill, _ in targets:
        if not (source_skill / "SKILL.md").is_file():
            print(f"invalid source skill: {source_skill}", file=sys.stderr)
            return 2
    existing = [destination for _, destination in targets if destination.exists() or destination.is_symlink()]
    if existing and not args.force:
        print(f"refusing to replace existing path: {existing[0]}", file=sys.stderr)
        return 1
    suite_temp = tempfile.TemporaryDirectory(prefix="a-stock-agent-wheel-")
    try:
        suite_wheel = _build_suite_wheel(source, Path(suite_temp.name))
        rollback: list[dict[str, str]] = []
        for destination in existing:
            backup = _backup(destination, root)
            rollback.append({"target": str(destination), "backup": str(backup)})
        manifest_path = root / ".local" / "share" / "a-stock-agent" / f"rollback-{time.time_ns()}.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        manifest_path.write_text(json.dumps({"release": release, "entries": rollback}, indent=2), encoding="utf-8")

        _install_runtime(source, root, lib_source, lib_wheel, suite_wheel)
        for source_skill, destination in targets:
            if destination.exists() or destination.is_symlink():
                if destination.is_dir() and not destination.is_symlink():
                    shutil.rmtree(destination)
                else:
                    destination.unlink()
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if args.mode == "symlink":
                destination.symlink_to(source_skill)
            else:
                shutil.copytree(source_skill, destination, symlinks=True)
                manifest = {
                    "release": release,
                    "source": str(source),
                    "source_hash": _tree_hash(source_skill),
                    "installed_at": time.time(),
                }
                (destination / ".a-stock-suite-manifest.json").write_text(
                    json.dumps(manifest, indent=2), encoding="utf-8"
                )
        for client in clients:
            for skill in SKILLS:
                if not (_target(root, client, skill) / "SKILL.md").is_file():
                    raise RuntimeError(f"client discovery validation failed: {_target(root, client, skill)}")
        print(f"installed release {release}; rollback manifest: {manifest_path}")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"install failed: {exc}", file=sys.stderr)
        return 1
    finally:
        suite_temp.cleanup()
