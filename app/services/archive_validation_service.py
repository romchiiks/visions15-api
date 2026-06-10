from pathlib import Path, PurePosixPath, PureWindowsPath

from fastapi import HTTPException, status


class ArchiveValidationService:
    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

    def validate_dataset_structure(
        self,
        extracted_dir: Path,
        metadata: dict,
    ) -> None:
        dataset_root = self._find_dataset_root(extracted_dir)

        for class_name, class_info in metadata["classes"].items():
            directory = self._validate_class_directory(
                class_name=class_name,
                directory=class_info["directory"],
            )
            expected_count = class_info["images_count"]

            class_dir = self._resolve_class_directory(
                dataset_root=dataset_root,
                directory=directory,
                class_name=class_name,
            )
            images_dir = class_dir / "images"
            self._ensure_path_inside_dataset(
                dataset_root=dataset_root,
                path=images_dir,
                class_name=class_name,
            )

            if not images_dir.exists():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Images directory not found for class {class_name}: {images_dir}",
                )

            if not images_dir.is_dir():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Images path is not a directory for class {class_name}: {images_dir}",
                )

            images = [
                path
                for path in images_dir.iterdir()
                if path.is_file()
                and path.suffix.lower() in self.ALLOWED_IMAGE_EXTENSIONS
            ]

            if len(images) != expected_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Images count mismatch for class {class_name}. "
                        f"Expected {expected_count}, found {len(images)}"
                    ),
                )

    def _validate_class_directory(self, class_name: str, directory: object) -> Path:
        if not isinstance(directory, str) or not directory.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"directory for class {class_name} must be a non-empty "
                    "relative path"
                ),
            )

        directory = directory.strip()
        posix_path = PurePosixPath(directory)
        windows_path = PureWindowsPath(directory)

        if (
            posix_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"directory for class {class_name} must be a relative path",
            )

        parts = directory.replace("\\", "/").split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"directory for class {class_name} must not contain empty, "
                    "current, or parent path segments"
                ),
            )

        return Path(directory)

    def _resolve_class_directory(
        self,
        dataset_root: Path,
        directory: Path,
        class_name: str,
    ) -> Path:
        resolved_dataset_root = dataset_root.resolve(strict=False)
        class_dir = (resolved_dataset_root / directory).resolve(strict=False)
        self._ensure_path_inside_dataset(
            dataset_root=resolved_dataset_root,
            path=class_dir,
            class_name=class_name,
        )

        return class_dir

    def _ensure_path_inside_dataset(
        self,
        dataset_root: Path,
        path: Path,
        class_name: str,
    ) -> None:
        resolved_dataset_root = dataset_root.resolve(strict=False)
        resolved_path = path.resolve(strict=False)

        try:
            resolved_path.relative_to(resolved_dataset_root)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"directory for class {class_name} must stay inside dataset",
            ) from exc

    def _find_dataset_root(self, extracted_dir: Path) -> Path:
        direct_metadata = extracted_dir / "metadata.json"

        if direct_metadata.exists():
            return extracted_dir

        candidates = list(extracted_dir.glob("*/metadata.json"))

        if len(candidates) == 1:
            return candidates[0].parent

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot determine dataset root directory",
        )
