from xml.sax.saxutils import escape

_XML_ATTRIBUTE_ESCAPES = {'"': "&quot;"}


class LabelConfigService:
    def build_object_detection_config(self, classes: list[str]) -> str:
        labels_xml = "\n".join(
            f'    <Label value="{escape(class_name, _XML_ATTRIBUTE_ESCAPES)}"/>'
            for class_name in classes
        )

        return f"""
<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="label" toName="image">
{labels_xml}
  </RectangleLabels>
</View>
""".strip()
