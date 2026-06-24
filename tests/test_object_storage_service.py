from app.services.object_storage_service import ObjectStorageService


def test_public_url_quotes_object_name():
    service = ObjectStorageService.__new__(ObjectStorageService)
    service.public_base_url = "https://storage.test/datasets"

    assert (
        service.public_url("datasets/archive/cat images/first image.JPG")
        == "https://storage.test/datasets/"
        "datasets/archive/cat%20images/first%20image.JPG"
    )
