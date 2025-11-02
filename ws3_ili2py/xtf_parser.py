from contextlib import contextmanager
from typing import Any, Optional, Type

from xsdata.formats.converter import Converter, converter
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.bases import Parsed
from xsdata.formats.dataclass.parsers.mixins import XmlNode
from xsdata.formats.types import T


@contextmanager
def temp_register(float_types: list, str_types: list, int_types: list, byte_type):
    registered = []
    try:

        class Ili2PyConverterClassBinBlBox(Converter):
            def deserialize(self, value: Any, **kwargs: Any) -> Type[byte_type]:
                from base64 import b64decode

                return byte_type(b64decode(value))

            def serialize(self, value: Any, **kwargs: Any) -> Optional[str]:
                from base64 import b64encode

                if value:
                    return b64encode(value).decode()
                else:
                    return None

        converter.register_converter(byte_type, Ili2PyConverterClassBinBlBox())

        for float_type in float_types:

            def deserialize(self, value: Any, **kwargs: Any) -> Type[float_type]:
                return float_type(value) if value else None

            def serialize(self, value: Any, **kwargs: Any) -> Optional[str]:
                return str(value) if value else None

            Ili2PyConverterClass = type(
                f"Converter{float_type.__name__}",
                (Converter,),
                {"deserialize": deserialize, "serialize": serialize},
            )
            converter.register_converter(float_type, Ili2PyConverterClass())
            registered.append(float_type)
        for str_type in str_types:

            def deserialize(self, value: Any, **kwargs: Any) -> Type[str_type]:
                return str_type(value) if value else None

            def serialize(self, value: Any, **kwargs: Any) -> Optional[str]:
                return str(value) if value else None

            Ili2PyConverterClass = type(
                f"Converter{str_type.__name__}",
                (Converter,),
                {"deserialize": deserialize, "serialize": serialize},
            )
            converter.register_converter(str_type, Ili2PyConverterClass())
            registered.append(str_type)
        for int_type in int_types:

            def deserialize(self, value: Any, **kwargs: Any) -> Type[int_type]:
                return int_type(value) if value else None

            def serialize(self, value: Any, **kwargs: Any) -> Optional[str]:
                return str(value) if value else None

            Ili2PyConverterClass = type(
                f"Converter{int_type.__name__}",
                (Converter,),
                {"deserialize": deserialize, "serialize": serialize},
            )
            converter.register_converter(int_type, Ili2PyConverterClass())
            registered.append(int_type)

        yield
    finally:
        for tp in registered:
            try:
                converter.unregister_converter(tp)
            except KeyError:
                pass


class IndexXmlParser(XmlParser):
    point_type: str = "point"
    line_type: str = "line"
    polygon_type: str = "polygon"

    def __init__(self, *args, callbacks=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.transfer_element_index = {}
        self.geometric_classes_index = {}

    def end(
        self,
        queue: list[XmlNode],
        objects: list[Parsed],
        qname: str,
        text: Optional[str],
        tail: Optional[str],
    ) -> T:
        successful = super().end(queue, objects, qname, text, tail)
        namespace, obj = objects[-1]
        if hasattr(obj, "TID"):
            identifier = obj.TID
        elif hasattr(obj, "tid"):
            identifier = obj.tid
        else:
            identifier = None
        if hasattr(obj, "metadata"):
            oid = obj.metadata["interlis"]["oid"]
            if identifier is not None:
                if oid not in self.transfer_element_index:
                    self.transfer_element_index[oid] = {}
                self.transfer_element_index[oid][identifier] = obj
                if len(obj.geom_attributes) > 0:
                    if oid not in self.geometric_classes_index:
                        self.geometric_classes_index[oid] = {
                            self.point_type: {},
                            self.line_type: {},
                            self.polygon_type: {},
                        }
                self.add_geometric_index_entry(
                    obj.geom_point_like_attribute_values,
                    identifier,
                    oid,
                    self.point_type,
                )
                self.add_geometric_index_entry(
                    obj.geom_line_like_attribute_values,
                    identifier,
                    oid,
                    self.line_type,
                )
                self.add_geometric_index_entry(
                    obj.geom_polygon_like_attribute_values,
                    identifier,
                    oid,
                    self.polygon_type,
                )
            else:
                if obj.metadata.get("interlis"):
                    if obj.metadata["interlis"].get("kind"):
                        if obj.metadata["interlis"]["kind"] in ["Association"]:
                            if oid not in self.transfer_element_index:
                                self.transfer_element_index[oid] = []
                            self.transfer_element_index[oid].append(obj)
        return successful

    def add_geometric_index_entry(self, values, identifier, oid, geometry_type):
        if len(values) > 0:
            if identifier not in self.geometric_classes_index[oid][geometry_type]:
                self.geometric_classes_index[oid][geometry_type][identifier] = []
            for attribute_name, geometry in values:
                if geometry is not None:
                    self.geometric_classes_index[oid][geometry_type][identifier].append(
                        (attribute_name, geometry)
                    )

    def clean_geometric_classes_index(self):
        """
        This method finally cleans out left over empty geometry arrays per identifier.
        """
        for oid in self.geometric_classes_index:
            for geometry_type in self.geometric_classes_index[oid]:
                for identifier in list(self.geometric_classes_index[oid][geometry_type].keys()):
                    if (
                        len(
                            self.geometric_classes_index[oid][geometry_type][identifier]
                        )
                        == 0
                    ):
                        del self.geometric_classes_index[oid][geometry_type][identifier]

    def parse(
        self,
        source: Any,
        clazz: Optional[type[T]] = None,
        ns_map: Optional[dict[Optional[str], str]] = None,
    ) -> T:
        result = super().parse(source, clazz, ns_map)
        self.clean_geometric_classes_index()
        return result
