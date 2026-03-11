import argparse

from . import core


def main() -> None:
    parser = argparse.ArgumentParser(prog="telnoti", description="Telegram notification CLI")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("setup", help="Configure bot token and chat ID")

    args = parser.parse_args()
    if args.command == "setup":
        core.setup()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
