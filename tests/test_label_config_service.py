from app.services.label_config_service import LabelConfigService


def test_build_object_detection_config_escapes_label_values():
    config = LabelConfigService().build_object_detection_config(
        classes=["cat", 'dog "quoted"', "fish & chips"]
    )

    assert '<Image name="image" value="$image"/>' in config
    assert '<RectangleLabels name="label" toName="image">' in config
    assert '<Label value="cat"/>' in config
    assert '<Label value="dog &quot;quoted&quot;"/>' in config
    assert '<Label value="fish &amp; chips"/>' in config
