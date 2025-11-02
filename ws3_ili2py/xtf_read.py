import logging
from typing import Tuple

from ili2py_interface.convertable_types import (
    get_special_float_types,
    get_special_int_types,
    get_special_str_types,
)
from ili2py_interface.references import BinBlBoxType
from ili2py_interface.xtf_opening import Transfer
from xsdata.formats.dataclass.parsers.config import ParserConfig
from xtf_parser import IndexXmlParser, temp_register

logging.getLogger().setLevel(logging.DEBUG)


def read(xtf_path: str) -> Tuple[IndexXmlParser, Transfer]:
    try:
        # we are in a ili23 environment
        from ili2py_interface.references import BinBlBox

        byte_type = BinBlBox
    except ImportError:
        # we are in a ili24 environment
        byte_type = BinBlBoxType

    with temp_register(
        get_special_float_types(),
        get_special_str_types(),
        get_special_int_types(),
        byte_type,
    ):
        parser_config = ParserConfig(
            fail_on_unknown_properties=False,
            fail_on_unknown_attributes=False,
        )
        parser = IndexXmlParser(parser_config)
        data = parser.parse(xtf_path, Transfer)
    return parser, data


# read(
#     "/home/kalle/projects/rudert-geoinformatik/ili2py/tests/data/models/OeREBKRMtrsfr_V2_0/ch.bazl.kataster-belasteter-standorte-zivilflugplaetze_v2_0.oereb.xtf"
# )
