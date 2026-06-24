import argparse
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from app.api.deps import get_model_storage_service
from app.services.model_storage_service import ModelStorageService


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="visions15ctl",
        description="Manage Visions15 model artifacts in MinIO",
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--new-model", action="store_true")
    action.add_argument("--roll-back", action="store_true")

    parser.add_argument("--source", type=Path)
    parser.add_argument("--target")
    parser.add_argument("--version")
    parser.add_argument("--model-version")
    parser.add_argument("--update-manifest", action="store_true")
    parser.add_argument("--class", dest="classes", action="append", default=[])
    parser.add_argument("--img-size", type=int)
    parser.add_argument("--model-type")
    parser.add_argument("--notes", default="")

    args = parser.parse_args()
    service = get_model_storage_service()
    _apply_target_override(service, args.target)

    if args.new_model:
        _publish_new_model(service, args)
        return

    _roll_back(service, args)


def _publish_new_model(service: ModelStorageService, args: argparse.Namespace) -> None:
    if args.source is None:
        raise SystemExit("--source is required with --new-model")

    release = datetime.now(timezone.utc).strftime("%d-%m-%Y")
    manifest = None
    source_path = args.source.resolve()

    if args.update_manifest:
        manifest = service.generate_manifest(
            sha256=service.sha256_file(source_path),
            version=args.model_version,
            classes=args.classes,
            img_size=args.img_size,
            model_type=args.model_type,
            notes=args.notes,
        )

    saved_manifest = service.upload_new_model(
        source_path=source_path,
        release=release,
        manifest=manifest,
    )
    _print_result("Model published", service, release, saved_manifest)


def _roll_back(service: ModelStorageService, args: argparse.Namespace) -> None:
    if not args.version:
        raise SystemExit("--version is required with --roll-back")

    manifest = None
    if args.update_manifest:
        release_manifest = None
        try:
            release_manifest = service.get_manifest(
                service.release_manifest_object_name(args.version)
            )
        except HTTPException as exc:
            if exc.status_code != 404:
                raise

        manifest = service.generate_manifest(
            sha256=service.sha256_object(
                service.release_model_object_name(args.version)
            ),
            version=args.model_version,
            classes=args.classes or None,
            img_size=args.img_size,
            model_type=args.model_type,
            notes=args.notes,
            base_manifest=release_manifest,
        )

    saved_manifest = service.roll_back(
        release=args.version,
        manifest=manifest,
    )
    _print_result("Model rolled back", service, args.version, saved_manifest)


def _apply_target_override(service: ModelStorageService, target: str | None) -> None:
    if not target:
        return

    clean_target = target.strip("/")
    if not clean_target:
        return

    parts = clean_target.split("/")
    if parts[-1] == "latest":
        parts = parts[:-1]

    if not parts:
        service.prefix = ""
        return

    if len(parts) == 1:
        if parts[0] == service.prefix:
            service.prefix = parts[0]
        else:
            service.bucket_name = parts[0]
            service.prefix = ""
        return

    service.bucket_name = parts[0]
    service.prefix = "/".join(parts[1:])


def _print_result(
    title: str,
    service: ModelStorageService,
    release: str,
    manifest: dict,
) -> None:
    print(title)
    print(f"Bucket: {service.bucket_name}")
    print(f"Latest model: {service.latest_model_object_name()}")
    print(f"Latest manifest: {service.latest_manifest_object_name()}")
    print(f"Release: {release}")
    print(f"Manifest version: {manifest.get('version')}")
    print(f"SHA256: {manifest.get('sha256')}")


if __name__ == "__main__":
    main()
