import argparse
import json
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from opencode_config.adapters.lemonade_client import HttpModelServerClient
from opencode_config.adapters.ollama_client import HttpOllamaClient
from opencode_config.adapters.server_registry import JsonServerRegistry
from opencode_config.adapters.opencode_config import JsonOpenCodeConfig
from opencode_config.domain.ports import ConfigError
from opencode_config.use_cases.sync import sync_models
from opencode_config.use_cases.list_servers import list_servers
from opencode_config.use_cases.server_management import (
    add_server,
    remove_server,
    set_server_enabled,
)


def _default_servers_path() -> Path:
    return Path.home() / ".config" / "opencode" / "local-inference-servers.json"


def _default_opencode_path() -> Path:
    local = Path.cwd() / "opencode.json"
    if local.exists():
        return local
    return Path.home() / ".config" / "opencode" / "opencode.json"


def _package_version() -> str:
    try:
        return version("occfg")
    except PackageNotFoundError:
        return "0.1.0"


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="occfg",
        description="Manage local inference servers and sync them into opencode.json",
    )
    parser.add_argument(
        "--servers",
        type=Path,
        default=_default_servers_path(),
        help="Server registry file",
    )
    parser.add_argument(
        "--opencode",
        type=Path,
        default=_default_opencode_path(),
        help="Target opencode config file",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"occfg {_package_version()}",
    )
    sub = parser.add_subparsers(dest="command")

    sync_p = sub.add_parser("sync", help="Refresh provider entries from enabled servers")
    sync_p.add_argument("-n", "--dry-run", action="store_true",
                        help="Print generated config to stdout, don't write")
    sync_p.add_argument("--show-all", action="store_true",
                        help="Include models that are not downloaded")

    server_p = sub.add_parser("server", help="Manage inference servers")
    server_sub = server_p.add_subparsers(dest="server_command")

    add_p = server_sub.add_parser("add", help="Register a server (probes it first)")
    add_p.add_argument("host")
    add_p.add_argument("--type", choices=["lemonade", "ollama"], default="lemonade")
    add_p.add_argument("--port", type=int)
    add_p.add_argument("--name", help="Display name (id is minted from it)")
    add_p.add_argument("--show-all", action="store_true",
                       help="Include models that are not downloaded")

    for verb, helptext in [
        ("remove", "Delete a server and its provider entry"),
        ("enable", "Re-enable a disabled server"),
        ("disable", "Disable a server without deleting it"),
    ]:
        p = server_sub.add_parser(verb, help=helptext)
        p.add_argument("id")

    list_p = server_sub.add_parser("list", help="List servers with model counts")
    list_p.add_argument("--show-all", action="store_true",
                        help="Count models that are not downloaded too")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = create_parser()
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if not argv or args.command is None:
        parser.print_help()
        return
    if args.command == "server" and args.server_command is None:
        parser.parse_args([args.command, "--help"])
        return

    try:
        code = _dispatch(args)
    except ConfigError as exc:
        print(exc)
        code = 2
    if code:
        sys.exit(code)


def _dispatch(args) -> int:
    registry = JsonServerRegistry(args.servers)
    clients = {
        "lemonade": HttpModelServerClient(),
        "ollama": HttpOllamaClient(),
    }
    opencode = JsonOpenCodeConfig(args.opencode)

    if args.command == "sync":
        result = sync_models(registry, clients, opencode,
                             dry_run=args.dry_run, show_all=args.show_all)
        for line in result.summary:
            print(f"✓ {line}")
        for line in result.warnings:
            print(f"⚠ {line}")
        for label, cause in result.failures:
            print(f"✗ {label}: {cause} — entry left unchanged, skipped")
        if args.dry_run:
            print(f"\n--- {args.opencode} (dry-run) ---")
            print(json.dumps(result.config.get("provider", {}), indent=2))
        elif result.wrote and not result.failures:
            print(f"✓ Updated providers in {args.opencode}")
        return 1 if result.failures else 0

    if args.command == "server":
        if args.server_command == "add":
            result = add_server(
                registry, clients, opencode, args.host,
                server_type=args.type, port=args.port, name=args.name,
                show_all=args.show_all,
            )
            print(result.message)
            return 0 if result.ok else 1
        if args.server_command in ("remove", "enable", "disable"):
            fn = {"remove": remove_server, "enable": set_server_enabled,
                  "disable": set_server_enabled}[args.server_command]
            if args.server_command == "remove":
                result = fn(registry, opencode, args.id)
            else:
                result = fn(registry, opencode, args.id,
                            enabled=(args.server_command == "enable"))
            print(result.message)
            return 0 if result.ok else 1
        if args.server_command == "list":
            results = list_servers(registry, clients, show_all=args.show_all)
            failed = False
            for r in results:
                location = f"{r['host']}:{r['port']}"
                if not r["enabled"]:
                    print(f"- {r['id']} — {r['name']} ({location}, {r['type']}) [disabled]")
                    continue
                if r["error"]:
                    print(f"✗ {r['id']} — {r['name']} ({location}, {r['type']}): {r['error']}")
                    failed = True
                    continue
                print(f"✓ {r['id']} — {r['name']} ({location}, {r['type']}): "
                      f"{len(r['models'])} chat models")
            return 1 if failed else 0

    return 0


if __name__ == "__main__":
    main()
