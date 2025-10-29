import logging
import os
import tempfile
from contextlib import contextmanager
from typing import Any, Iterable, Optional, Type

from xsdata.formats.converter import Converter, converter
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.bases import Parsed
from xsdata.formats.dataclass.parsers.config import ParserConfig
from xsdata.formats.dataclass.parsers.mixins import XmlNode
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.types import T

logging.getLogger().setLevel(logging.DEBUG)

from interface.convertable_types import (
    get_contained_model_names,
    get_special_float_types,
    get_special_int_types,
    get_special_str_types,
)
from interface.references import BinBlBoxType, XmlBlBoxType
from interface.xtf_opening import Transfer


class IndexXmlParser(XmlParser):
    def __init__(self, *args, callbacks=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.transfer_element_index = {}

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
        if hasattr(obj, 'TID'):
            identifier = obj.TID
        elif hasattr(obj, 'tid'):
            identifier = obj.tid
        else:
            identifier = None
        if identifier is not None:
            oid = obj.metadata['interlis']['oid']
            if oid not in self.transfer_element_index:
                self.transfer_element_index[oid] = {}
            self.transfer_element_index[oid][identifier] = obj
        return successful


@contextmanager
def temp_register():
    registered = []
    float_types = get_special_float_types()
    str_types = get_special_str_types()
    int_types = get_special_int_types()
    try:
        try:
            # we are in a ili23 environment
            from interface.references import BinBlBox
            class Ili2PyConverterClassBinBlBox(Converter):
                def deserialize(self, value: Any, **kwargs: Any) -> BinBlBox:
                    from base64 import b64decode

                    return BinBlBox(b64decode(value))

                def serialize(self, value: Any, **kwargs: Any) -> Optional[str]:
                    from base64 import b64encode

                    if value:
                        return b64encode(value).decode()
                    else:
                        return None

            converter.register_converter(BinBlBox, Ili2PyConverterClassBinBlBox())
        except ImportError as e:
            # we are in a ili24 environment
            class Ili2PyConverterClassBinBlBoxType(Converter):
                def deserialize(self, value: Any, **kwargs: Any) -> BinBlBoxType:
                    from base64 import b64decode

                    return BinBlBoxType(b64decode(value))

                def serialize(self, value: Any, **kwargs: Any) -> Optional[str]:
                    from base64 import b64encode

                    if value:
                        return b64encode(value).decode()
                    else:
                        return None

            converter.register_converter(BinBlBoxType, Ili2PyConverterClassBinBlBoxType())
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


parser_config = ParserConfig(
    fail_on_unknown_properties=False,
    fail_on_unknown_attributes=False,
)
with temp_register():
    parser = IndexXmlParser(parser_config)
    xtf_path = "models/OeREBKRMtrsfr_V2_0/ch.bazl.kataster-belasteter-standorte-zivilflugplaetze_v2_0.oereb.xtf"
    data = parser.parse(xtf_path, Transfer)
    data.headersection.sender = 'ili2py was here'
    out_xtf_path = "manipulated.xtf"
    with open(out_xtf_path, mode="w+") as f:
        f.write(XmlSerializer().render(data, ns_map={"ili": "http://www.interlis.ch/INTERLIS2.3"}))
