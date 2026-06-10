import argparse

from app.core.config import settings
from app.services.api_key_service import ApiKeyService


def create_key(name: str) -> None:
    service = ApiKeyService(settings.API_KEYS_FILE)
    api_key = service.create_key(name)

    print("API key created.")
    print()
    print(f"Name: {name}")
    print(f"Key:  {api_key}")
    print()
    print("Save this key now. It will not be shown again.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage desktop API keys"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--name", required=True)

    args = parser.parse_args()

    if args.command == "create":
        create_key(args.name)


if __name__ == "__main__":
    main()