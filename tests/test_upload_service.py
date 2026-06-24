from app.services.archive_validation_service import ArchiveValidationService
from app.services.upload_service import UploadService


class FakeObjectStorageService:
    def __init__(self):
        self.uploads = []

    def upload_file(self, source_path, object_name):
        self.uploads.append({"source_path": source_path, "object_name": object_name})
        return f"https://storage.test/{object_name.replace(' ', '%20')}"


def test_build_label_studio_tasks_uploads_images_to_object_storage(tmp_path):
    extracted_dir = tmp_path / "extracted" / "archive"
    images_dir = extracted_dir / "cat" / "images"
    images_dir.mkdir(parents=True)
    (extracted_dir / "metadata.json").write_text("{}", encoding="utf-8")
    (images_dir / "first image.JPG").write_bytes(b"image")
    (images_dir / "ignored.txt").write_text("not image", encoding="utf-8")
    object_storage_service = FakeObjectStorageService()

    service = UploadService(
        archive_service=None,
        metadata_service=None,
        archive_validation_service=ArchiveValidationService(),
        object_storage_service=object_storage_service,
        project_service=None,
    )

    tasks = service._build_label_studio_tasks(
        extracted_dir=extracted_dir,
        metadata={
            "classes": {
                "cat": {
                    "article": "cat article",
                    "directory": "cat",
                    "images_count": 1,
                }
            }
        },
    )

    assert tasks == [
        {
            "data": {
                "image": (
                    "https://storage.test/"
                    "datasets/archive/cat/images/first%20image.JPG"
                ),
            },
            "meta": {
                "class": "cat",
                "article": "cat article",
                "source_path": "datasets/archive/cat/images/first image.JPG",
            },
        }
    ]
    assert object_storage_service.uploads == [
        {
            "source_path": images_dir / "first image.JPG",
            "object_name": "datasets/archive/cat/images/first image.JPG",
        }
    ]


def test_build_label_studio_tasks_by_class_groups_images(tmp_path):
    extracted_dir = tmp_path / "extracted" / "archive"
    cat_images_dir = extracted_dir / "cat" / "images"
    dog_images_dir = extracted_dir / "dog" / "images"
    cat_images_dir.mkdir(parents=True)
    dog_images_dir.mkdir(parents=True)
    (extracted_dir / "metadata.json").write_text("{}", encoding="utf-8")
    (cat_images_dir / "cat.jpg").write_bytes(b"image")
    (dog_images_dir / "dog.png").write_bytes(b"image")
    object_storage_service = FakeObjectStorageService()

    service = UploadService(
        archive_service=None,
        metadata_service=None,
        archive_validation_service=ArchiveValidationService(),
        object_storage_service=object_storage_service,
        project_service=None,
    )

    tasks_by_class = service._build_label_studio_tasks_by_class(
        extracted_dir=extracted_dir,
        metadata={
            "classes": {
                "cat": {
                    "article": "cat article",
                    "directory": "cat",
                    "images_count": 1,
                },
                "dog": {
                    "article": "dog article",
                    "directory": "dog",
                    "images_count": 1,
                },
            }
        },
    )

    assert list(tasks_by_class) == ["cat", "dog"]
    assert [task["meta"]["class"] for task in tasks_by_class["cat"]] == ["cat"]
    assert [task["meta"]["class"] for task in tasks_by_class["dog"]] == ["dog"]
    assert len(object_storage_service.uploads) == 2
