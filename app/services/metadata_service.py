import json
from pathlib import Path

from fastapi import HTTPException, status


class MetadataService:
    def read_metadata(self, extracted_dir: Path) -> dict:
        metadata_path = self._find_metadata_file(extracted_dir)

        try:
            with metadata_path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid metadata.json: malformed JSON",
            ) from exc

    def validate_metadata(self, metadata: dict) -> None:
        if not isinstance(metadata, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="metadata.json must contain a JSON object",
            )

        if metadata.get("schema_version") != "1.0":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported or missing metadata schema_version",
            )

        if "dataset_update" not in metadata:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing dataset_update block in metadata.json",
            )

        dataset_update = metadata["dataset_update"]

        if not isinstance(dataset_update, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="metadata.dataset_update must be an object",
            )

        project_name = dataset_update.get("name")
        if not isinstance(project_name, str) or not project_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="metadata.dataset_update.name must be a non-empty string",
            )

        if "classes" not in metadata:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing classes block in metadata.json",
            )

        if not isinstance(metadata["classes"], dict) or not metadata["classes"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="metadata.classes must be a non-empty object",
            )

        for class_name, class_info in metadata["classes"].items():
            if not class_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Class name cannot be empty",
                )

            if not isinstance(class_info, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"metadata.classes.{class_name} must be an object",
                )

            if "article" not in class_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing article for class {class_name}",
                )

            if "directory" not in class_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing directory for class {class_name}",
                )

            if "images_count" not in class_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing images_count for class {class_name}",
                )

            images_count = class_info["images_count"]
            if (
                not isinstance(images_count, int)
                or isinstance(images_count, bool)
                or images_count < 0
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"images_count for class {class_name} must be an integer >= 0",
                )

    def _find_metadata_file(self, extracted_dir: Path) -> Path:
        direct_metadata = extracted_dir / "metadata.json"

        if direct_metadata.exists():
            return direct_metadata

        candidates = list(extracted_dir.glob("*/metadata.json"))

        if len(candidates) == 1:
            return candidates[0]

        if not candidates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="metadata.json not found in archive",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple metadata.json files found in archive",
        )
