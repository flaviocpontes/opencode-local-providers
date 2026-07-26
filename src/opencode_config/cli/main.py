import argparse
import sys
from pathlib import Path

from opencode_config.adapters.lemonade_client import HttpLemonadeClient
from opencode_config.adapters.server_registry import JsonServerRegistry
from opencode_config.adapters.opencode_config import JsonOpenCodeConfig
from opencode_config.use_cases.sync import sync_models
from opencode_config.use_cases.list_servers import list_servers


def _default_servers_path() -> Path:
    return Path.home() / ".config" / "opencode" / "local-inference-servers.json"


def _default_opencode_path() -> Path:
    local = Path.cwd() / "opencode.json"
    if local.exists():
        return local
    return Path.home() / ".config" / "opencode" / "opencode.json"


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opencode_config",
        description="Sync Lemonade Server models into opencode.json",
    )
    parser.add_argument(
        "--servers",
        type=Path,
        default=_default_servers_path(),
        help="Lemonade server registry file",
    )
    parser.add_argument(
        "--opencode",
        type=Path,
        default=_default_opencode_path(),
        help="Target opencode config file",
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Include models that are not downloaded",
    )
    parser.add_argument(
        "-l",
        "--list-servers",
        action="store_true",
        help="Print server registry with model summaries and exit",
    )
    parser.add_argument(
        "--init-servers",
        action="store_true",
        help="Create a default server registry file and exit",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Print generated config to stdout, don't write",
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.version:
        print("opencode_config 0.1.0")
        return

    servers_path: Path = args.servers
    opencode_path: Path = args.opencode

    if args.init_servers:
        if servers_path.exists():
            print(f"File already exists: {servers_path}")
            return
        servers_path.parent.mkdir(parents=True, exist_ok=True)
        template = {
            "servers": [
                {
                    "host": "192.168.0.20",
                    "port": 13305,
                    "name": "Lemonade Desktop",
                },
            ]
        }
        import json
        servers_path.write_text(json.dumps(template, indent=2) + "\n")
        print(f"Created {servers_path} — edit with your server addresses and re-run.")
        return

    if not servers_path.exists():
        print(f"Server registry not found: {servers_path}")
        print("Run with --init-servers to create one.")
        sys.exit(1)

    server_registry = JsonServerRegistry(servers_path)
    lemonade = HttpLemonadeClient()
    opencode = JsonOpenCodeConfig(opencode_path)

    if args.list_servers:
        results = list_servers(server_registry, lemonade)
        for r in results:
            print(f"{r['name']} ({r['host']}:{r['port']})")
            for m in r["models"]:
                flags = " ".join(m.labels)
                ctx = f"{m.max_context_window // 1000}K" if m.max_context_window else "?"
                print(f"  {m.id:45s} {ctx:>6s}  {flags}")
        return

    results = sync_models(server_registry, lemonade, opencode)
    for line in results:
        print(f"✓ {line}")

    if args.dry_run:
        # Re-read and print what was written
        raw = opencode_path.read_text() if opencode_path.exists() else "{}"
        print(f"\n--- {opencode_path} (dry-run) ---\n{raw}")
    else:
        print(f"✓ Updated providers in {opencode_path}")


if __name__ == "__main__":
    main()
