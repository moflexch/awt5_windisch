import logging

from xsdata.formats.dataclass.serializers import XmlSerializer
from xtf_read import read

logging.getLogger().setLevel(logging.DEBUG)


def write(xtf_path: str):
    parser, data = read(xtf_path)
    data.headersection.sender = "ili2py was here"
    out_xtf_path = "manipulated.xtf"
    with open(out_xtf_path, mode="w+") as f:
        f.write(
            XmlSerializer().render(
                data, ns_map={"ili": "http://www.interlis.ch/INTERLIS2.3"}
            )
        )


write(
    "models/OeREBKRMtrsfr_V2_0/ch.bazl.kataster-belasteter-standorte-zivilflugplaetze_v2_0.oereb.xtf"
)
