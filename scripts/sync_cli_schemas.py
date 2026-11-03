#!/usr/bin/env python3
"""Sync and verify MediaKit CLI capability schemas for the plugin.

The MediaKit CLI is evolving quickly (tool names, parameters and supported
modes change between releases). This script snapshots the JSON Schema of every
CLI capability into ``schemas/`` together with a ``manifest.json`` fingerprint,
so the plugin can:

- detect command/parameter drift before publishing a new node version (CI);
- declare the exact CLI version range a release was validated against;
- decide at runtime whether a capability supports ``--local`` execution.

Usage
-----
    python scripts/sync_cli_schemas.py                 # check drift (CI-safe)
    python scripts/sync_cli_schemas.py --update        # refresh snapshots
    python scripts/sync_cli_schemas.py --update --cli /path/to/mediakit-cli
    python scripts/sync_cli_schemas.py --check --json  # machine-readable report
    python scripts/sync_cli_schemas.py --offline       # validate snapshots only

Exit codes
----------
    0  snapshots are consistent with the installed CLI (or --offline validated)
    1  drift detected (new/removed tools or changed schemas) or an error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMAS_DIR = REPO_ROOT / "schemas"
MANIFEST_NAME = "manifest.json"

_DOMAINS_ROW = re.compile(r"^([a-z-]+)\t(\d+)\t(.*)$", re.IGNORECASE)
_TOOL_LINE = re.compile(r"^-\s+([a-z][a-z0-9-]*)\s", re.IGNORECASE)
_MODE_LINE = re.compile(r"支持模式\s*:\s*(.+)", re.IGNORECASE)


@dataclass(frozen=True)
class ToolSnapshot:
    domain: str
    tool: str
    fingerprint: str
    modes: tuple[str, ...] = ()


def run_cli(cli: str, arguments: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """Run the CLI without a shell."""
    return subprocess.run(
        [cli, *arguments],
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        check=False,
    )


def parse_domains(output: str) -> list[tuple[str, str]]:
    """Parse ``mediakit-cli --domains`` TSV output into (domain, description)."""
    domains: list[tuple[str, str]] = []
    for line in output.splitlines():
        match = _DOMAINS_ROW.match(line.strip())
        if match:
            domains.append((match.group(1), match.group(3)))
    return domains


def parse_tools(output: str) -> list[str]:
    """Parse ``mediakit-cli <domain> --help`` output into tool names."""
    tools: list[str] = []
    for line in output.splitlines():
        match = _TOOL_LINE.match(line.strip())
        if match:
            tools.append(match.group(1))
    return tools


def parse_modes(output: str) -> tuple[str, ...]:
    """Parse supported modes (e.g. ``支持模式: Cloud, Local``) from help text."""
    modes: list[str] = []
    for line in output.splitlines():
        match = _MODE_LINE.search(line)
        if match:
            for token in match.group(1).split(","):
                token = token.strip()
                if token:
                    modes.append(token)
    return tuple(dict.fromkeys(modes))


def fingerprint(value: dict) -> str:
    """Return a stable sha256 fingerprint for a schema snapshot."""
    normalized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def cli_version(cli: str) -> str:
    result = run_cli(cli, ["version"], timeout=30)
    text = (result.stdout or result.stderr).strip()
    match = re.search(r"(\d+\.\d+\.\d+)", text)
    return match.group(1) if match else text.splitlines()[0] if text else "unknown"


def collect_snapshots(
    cli: str,
) -> tuple[str, dict[str, list[ToolSnapshot]]]:
    """Fetch the schema of every tool exposed by the installed CLI.

    Returns (cli_version, {domain: [ToolSnapshot, ...]}).
    """
    domains = parse_domains(run_cli(cli, ["--domains"]).stdout)
    by_domain: dict[str, list[ToolSnapshot]] = {}
    for domain, _description in domains:
        tools = parse_tools(run_cli(cli, [domain, "--help"]).stdout)
        snapshots: list[ToolSnapshot] = []
        for tool in tools:
            schema_result = run_cli(cli, [domain, tool, "--schema"], timeout=120)
            if schema_result.returncode != 0:
                print(
                    f"  [warn] {domain}/{tool}: --schema failed "
                    f"(exit {schema_result.returncode}); skipping.",
                    file=sys.stderr,
                )
                continue
            try:
                schema = json.loads(schema_result.stdout)
            except json.JSONDecodeError:
                print(f"  [warn] {domain}/{tool}: --schema output is not JSON; skipping.", file=sys.stderr)
                continue
            modes = parse_modes(run_cli(cli, [domain, tool, "--help"]).stdout)
            snapshots.append(
                ToolSnapshot(
                    domain=domain,
                    tool=tool,
                    fingerprint=fingerprint(schema),
                    modes=modes,
                )
            )
        by_domain[domain] = snapshots
    return cli_version(cli), by_domain


def write_snapshots(
    schemas_dir: Path,
    cli_version_text: str,
    by_domain: dict[str, list[ToolSnapshot]],
) -> None:
    """Store normalized schema snapshots plus a versioned manifest."""
    for domain, snapshots in by_domain.items():
        domain_dir = schemas_dir / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        for snapshot in snapshots:
            (domain_dir / f"{snapshot.tool}.json").write_text(
                json.dumps(
                    {
                        "domain": domain,
                        "tool": snapshot.tool,
                        "modes": list(snapshot.modes),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
    manifest = {
        "format": 1,
        "cli_version": cli_version_text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domains": {
            domain: [
                {
                    "tool": snapshot.tool,
                    "fingerprint": snapshot.fingerprint,
                    "modes": list(snapshot.modes),
                }
                for snapshot in snapshots
            ]
            for domain, snapshots in sorted(by_domain.items())
        },
    }
    (schemas_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_manifest(schemas_dir: Path) -> dict | None:
    manifest_path = schemas_dir / MANIFEST_NAME
    if not manifest_path.is_file():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def diff_report(
    current_version: str,
    current: dict[str, list[ToolSnapshot]],
    previous: dict,
) -> tuple[bool, list[str]]:
    """Compare current snapshots with a stored manifest.

    Returns (drifted, report_lines). A tool is considered changed when its
    schema fingerprint differs from the stored one.
    """
    report: list[str] = []
    drifted = current_version != previous.get("cli_version")

    current_tools = {
        (domain, snapshot.tool): snapshot
        for domain, snapshots in current.items()
        for snapshot in snapshots
    }
    previous_domains = previous.get("domains", {})
    previous_tools = {
        (domain, entry["tool"]): entry
        for domain, entries in previous_domains.items()
        for entry in entries
    }

    if drifted:
        report.append(
            f"CLI 版本变化：快照 {previous.get('cli_version')} → 当前 {current_version}，"
            "请运行 --update 重新验证后发布。"
        )

    for tool_key in sorted(set(previous_tools) - set(current_tools)):
        report.append(f"工具消失：{tool_key[0]}/{tool_key[1]}（快照中存在，当前 CLI 已移除）")
    for tool_key in sorted(set(current_tools) - set(previous_tools)):
        report.append(f"工具新增：{tool_key[0]}/{tool_key[1]}（当前 CLI 新增，节点尚未覆盖）")

    for tool_key in sorted(set(current_tools) & set(previous_tools)):
        current_snapshot = current_tools[tool_key]
        previous_entry = previous_tools[tool_key]
        if current_snapshot.fingerprint != previous_entry.get("fingerprint"):
            report.append(
                f"参数变化：{tool_key[0]}/{tool_key[1]}（schema 指纹不一致）"
            )
        current_modes = set(current_snapshot.modes)
        previous_modes = set(previous_entry.get("modes", []))
        if current_modes != previous_modes:
            report.append(
                f"模式变化：{tool_key[0]}/{tool_key[1]} "
                f"（{sorted(previous_modes)} → {sorted(current_modes)}）"
            )

    return bool(report), report


def validate_snapshot_tree(schemas_dir: Path) -> list[str]:
    """Offline validation of the snapshot tree without invoking the CLI."""
    errors: list[str] = []
    manifest = _load_manifest(schemas_dir)
    if manifest is None:
        return ["缺少 schemas/manifest.json（请先运行 --update 生成快照）。"]
    for domain, entries in manifest.get("domains", {}).items():
        for entry in entries:
            snapshot_path = schemas_dir / domain / f"{entry['tool']}.json"
            if not snapshot_path.is_file():
                errors.append(f"缺少快照文件：{snapshot_path.relative_to(schemas_dir)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="刷新 schema 快照")
    parser.add_argument("--check", action="store_true", help="对比当前 CLI 与快照（默认行为）")
    parser.add_argument("--cli", default="mediakit-cli", help="mediakit-cli 可执行文件路径")
    parser.add_argument("--schemas-dir", default=str(DEFAULT_SCHEMAS_DIR), help="快照目录")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出 check 结果")
    parser.add_argument("--offline", action="store_true", help="不调用 CLI，仅校验快照树")
    args = parser.parse_args(argv)

    schemas_dir = Path(args.schemas_dir)

    if args.offline:
        errors = validate_snapshot_tree(schemas_dir)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        print(f"快照树完整（{schemas_dir}）")
        return 0

    if not os.environ.get("PATH", ""):
        print("[warn] PATH 为空，请确保 mediakit-cli 在 PATH 中。", file=sys.stderr)

    if args.update:
        print(f"正在同步 CLI schema（CLI: {args.cli}）…")
        version, snapshots = collect_snapshots(args.cli)
        write_snapshots(schemas_dir, version, snapshots)
        tool_count = sum(len(items) for items in snapshots.values())
        print(
            f"完成：{version} 共 {tool_count} 个工具已写入 {schemas_dir}"
            f"（{len(snapshots)} 个域）"
        )
        return 0

    # Default: drift check.
    try:
        version, snapshots = collect_snapshots(args.cli)
    except FileNotFoundError:
        print(
            f"找不到 CLI：{args.cli}。请先安装 mediakit-cli，或使用 --offline 校验快照。",
            file=sys.stderr,
        )
        return 1

    previous = _load_manifest(schemas_dir)
    if previous is None:
        print(
            f"缺少 manifest（{schemas_dir / MANIFEST_NAME}）。请先运行 --update 生成基线。",
            file=sys.stderr,
        )
        return 1

    drifted, report = diff_report(version, snapshots, previous)
    if args.json:
        print(
            json.dumps(
                {
                    "ok": not drifted,
                    "cli_version": version,
                    "snapshot_cli_version": previous.get("cli_version"),
                    "drift": report,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    elif drifted:
        print(f"检测到 schema 漂移（CLI {version}）：")
        for line in report:
            print(f"  - {line}")
    else:
        print(f"无漂移：CLI {version} 与快照一致（{sum(len(v) for v in snapshots.values())} 个工具）。")
    return 1 if drifted else 0


if __name__ == "__main__":
    sys.exit(main())
