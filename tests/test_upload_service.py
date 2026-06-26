import asyncio

from app.services.archive_validation_service import ArchiveValidationService
from app.services.upload_service import UploadService


class FakeObjectStorageService:
    def __init__(self, events=None):
        self.uploads = []
        self.events = events

    def upload_file(self, source_path, object_name):
        if self.events is not None:
            self.events.append("upload_file")
        self.uploads.append({"source_path": source_path, "object_name": object_name})
        return f"https://storage.test/{object_name.replace(' ', '%20')}"


class FakeArchiveService:
    def __init__(self, archive_path, extracted_dir, events):
        self.archive_path = archive_path
        self.extracted_dir = extracted_dir
        self.events = events

    async def save_archive(self, archive):
        self.events.append("save_archive")
        return self.archive_path

    def extract_archive(self, archive_path):
        self.events.append("extract_archive")
        return self.extracted_dir


class FakeMetadataService:
    def __init__(self, metadata, events):
        self.metadata = metadata
        self.events = events

    def read_metadata(self, extracted_dir):
        self.events.append("read_metadata")
        return self.metadata

    def validate_metadata(self, metadata):
        self.events.append("validate_metadata")


class FakeArchiveValidationService(ArchiveValidationService):
    def __init__(self, events):
        self.events = events

    def validate_dataset_structure(self, extracted_dir, metadata):
        self.events.append("validate_dataset_structure")


class FakePerspectiveWarpService:
    def __init__(self, events):
        self.events = events
        self.image_paths = []

    def warp_images(self, image_paths):
        self.events.append("warp_images")
        self.image_paths = list(image_paths)


class FakeProjectService:
    def __init__(self, events):
        self.events = events
        self.tasks_by_class = None

    async def create_projects_from_metadata_with_tasks_by_class(
        self,
        metadata,
        tasks_by_class,
    ):
        self.events.append("create_projects")
        self.tasks_by_class = tasks_by_class
        return [
            {
                "project_id": 1,
                "project_name": "cat-dataset",
                "class_name": "cat",
                "imported_tasks_count": len(tasks_by_class["cat"]),
            }
        ]


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


def test_process_archive_upload_warps_extracted_images_before_upload(tmp_path):
    events = []
    archive_path = tmp_path / "uploads" / "archive.zip"
    extracted_dir = tmp_path / "extracted" / "archive"
    images_dir = extracted_dir / "cat" / "images"
    archive_path.parent.mkdir()
    images_dir.mkdir(parents=True)
    archive_path.write_bytes(b"archive")
    (extracted_dir / "metadata.json").write_text("{}", encoding="utf-8")
    image_path = images_dir / "cat.jpg"
    image_path.write_bytes(b"image")
    metadata = {
        "classes": {
            "cat": {
                "article": "cat article",
                "directory": "cat",
                "images_count": 1,
            }
        }
    }
    object_storage_service = FakeObjectStorageService(events)
    perspective_warp_service = FakePerspectiveWarpService(events)
    project_service = FakeProjectService(events)

    service = UploadService(
        archive_service=FakeArchiveService(archive_path, extracted_dir, events),
        metadata_service=FakeMetadataService(metadata, events),
        archive_validation_service=FakeArchiveValidationService(events),
        object_storage_service=object_storage_service,
        project_service=project_service,
        perspective_warp_service=perspective_warp_service,
    )

    result = asyncio.run(service.process_archive_upload(archive=None))

    assert events == [
        "save_archive",
        "extract_archive",
        "read_metadata",
        "validate_metadata",
        "validate_dataset_structure",
        "warp_images",
        "upload_file",
        "create_projects",
    ]
    assert perspective_warp_service.image_paths == [image_path]
    assert object_storage_service.uploads == [
        {
            "source_path": image_path,
            "object_name": "datasets/archive/cat/images/cat.jpg",
        }
    ]
    assert result["status"] == "success"
    assert result["imported_tasks_count"] == 1
