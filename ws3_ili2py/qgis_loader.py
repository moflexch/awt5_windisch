# Diesen Pfad nach Wunsch anpassen:
xtf_path = "models/OeREBKRMtrsfr_V2_0/ch.bazl.kataster-belasteter-standorte-zivilflugplaetze_v2_0.oereb.xtf"
# xtf_path = "models/SZ_Waldfeststellungen_V2/SZ_Waldfeststellungen_V2.xtf"


import base64
import logging
import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import fields
from typing import Any, Optional, Type

from xsdata.formats.converter import Converter, converter
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.bases import Parsed
from xsdata.formats.dataclass.parsers.config import ParserConfig
from xsdata.formats.dataclass.parsers.mixins import XmlNode
from xsdata.formats.types import T
from qgis.core import (QgsVectorLayer,QgsFeature, QgsPointXY, QgsGeometry, QgsProject, QgsField, QgsApplication)
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QVariant, QCoreApplication

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
xtf_path = os.path.join(script_dir, xtf_path)

logging.getLogger().setLevel(logging.DEBUG)

from interface.convertable_types import (
    get_special_float_types,
    get_special_int_types,
    get_special_str_types,
)
from interface.references import BinBlBoxType, Ref
from interface.xtf_opening import Transfer


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

dialog = QtWidgets.QDialog()
dialog.setWindowTitle("XTF-Browser")
dialog.resize(400, 300)
text_browser = QtWidgets.QTextBrowser(dialog)

# Signal für Resize des Dialogs
def on_resize(event):
    return super(QtWidgets.QDialog, dialog).resizeEvent(event)

dialog.resizeEvent = on_resize
layout = QtWidgets.QVBoxLayout()
layout.addWidget(text_browser)
dialog.setLayout(layout)


class IndexXmlParser(XmlParser):
    def __init__(self, *args, callbacks=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.transfer_element_index: dict = {}
        self._process_batch: list = []
        self.qgis_ili_layer_registry: dict = {}
        self.feature_linker: dict = {}
        self._process_batch_size: int = 10000

    def parse(
        self,
        source: Any,
        clazz: Optional[type[T]] = None,
        ns_map: Optional[dict[Optional[str], str]] = None,
    ) -> T:
        result = super().parse(source, clazz, ns_map)
        # finally process all leftover features
        if len(self._process_batch) > 0:
            self.qgis_stuff()
        return result

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
        self._process_batch.append(obj)
        if len(self._process_batch) == self._process_batch_size:
            self.qgis_stuff()
        return successful

    def render_result(self, ili_objects):
        feature_texts = []
        for ili_object, layer_name in ili_objects:
            feature_text = [f'<p><h2>{layer_name}</h2><table style="width:100%; border:1px solid #555; border-collapse:collapse;">']
            for field in fields(ili_object):
                name = field.name
                if name not in ili_object.geom_attributes:
                    value = getattr(ili_object, name)
                    if isinstance(value, Ref):
                        feature_text.append(f'<tr><td>{name}</td><td><a href="aktion:info:{field.metadata['interlis']["reference_targets"][0]}:{value.ref}">{value}</a></td></tr>')
                    elif isinstance(value, BinBlBoxType):
                        feature_text.append(f'<tr><td style="width:200px; text-align:center; vertical-align:middle;">{name}</td><td><img style="width:100%; height:auto;" src="data:image/png;base64,{base64.b64encode(value.BINBLBOX).decode('ascii')}"></td></tr>')
                        # feature_text.append(f'<li>{name}: {value.BINBLBOX}</li>')
                    else:
                        feature_text.append(f'<tr><td style="padding:10px;">{name}</td><td>{value}</td></tr>')
            feature_text.append("</table></p>")
            feature_texts.append('\n'.join(feature_text))
            text_browser.setHtml(f"""
                        <h1>Selektierte Elemente:</h1>
                        {'\n'.join(feature_texts)}
                        """)
        dialog.show()

    def qgis_stuff(self):
        def on_selection_changed(selected, deselected, clear_and_select):
            ili_objects = []
            for oid_key in self.qgis_ili_layer_registry:
                for layer_name_key in self.qgis_ili_layer_registry[oid_key]:
                    layer = self.qgis_ili_layer_registry[oid_key][layer_name_key]
                    selected_features = layer.selectedFeatures()
                    for feature in selected_features:
                        ili_object = self.feature_linker[feature["uuid"]]
                        ili_objects.append((ili_object, layer_name_key))
            self.render_result(ili_objects)


        qgis_feature_batches = {}

        for obj in self._process_batch:
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
                # obj.Punkt.metadata['interlis']['meta_attributes']['CRS']
                geom_point_values = obj.geom_point_like_attribute_values
                # obj.Linie.__dataclass_fields__["POLYLINE"].metadata['interlis']['meta_attributes']['CRS']
                geom_line_values = obj.geom_line_like_attribute_values
                # obj.Flaeche.__dataclass_fields__["SURFACE"].metadata['interlis']['meta_attributes']['CRS']
                geom_polygon_values = obj.geom_polygon_like_attribute_values
                if len(geom_point_values) > 0 or len(geom_line_values) > 0 or len(geom_polygon_values) > 0:
                    layer_name = f"{oid}-point"
                    if oid not in self.qgis_ili_layer_registry:
                        self.qgis_ili_layer_registry[oid] = {}
                    if oid not in qgis_feature_batches:
                        qgis_feature_batches[oid] = {}
                    if len(geom_point_values) > 0:
                        attribute_name, geometry = geom_point_values[0]
                        if geometry:
                            if layer_name not in self.qgis_ili_layer_registry[oid]:
                                meta_attributes = geom_polygon_values[0][1].__dataclass_fields__["SURFACE"].metadata['interlis']['meta_attributes']
                                layer = QgsVectorLayer(
                                    f"Point?crs={meta_attributes.get('CRS') or 'EPSG:2056'}", layer_name, "memory"
                                )
                                self.qgis_ili_layer_registry[oid][layer_name] = layer
                                QgsProject.instance().addMapLayer(layer)

                                # connect to function
                                layer.selectionChanged.connect(on_selection_changed)
                            else:
                                layer = self.qgis_ili_layer_registry[oid][layer_name]
                            if layer_name not in qgis_feature_batches[oid]:
                                qgis_feature_batches[oid][layer_name] = []
                            feature_batch = qgis_feature_batches[oid][layer_name]
                            pr = layer.dataProvider()
                            pr.addAttributes([
                                QgsField("uuid", QVariant.String)
                            ])
                            layer.updateFields()
                            for attribute_name, point in geom_point_values:
                                f = QgsFeature(layer.fields())
                                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point.coord.C1, point.coord.C2)))
                                f["uuid"] = str(uuid.uuid4())
                                feature_batch.append(f)
                                self.feature_linker[f["uuid"]] = obj
                    if len(geom_polygon_values) > 0:
                        attribute_name, geometry = geom_polygon_values[0]
                        if geometry:
                            layer_name = f"{oid}-polygon"
                            if layer_name not in self.qgis_ili_layer_registry[oid]:
                                meta_attributes = geom_polygon_values[0][1].__dataclass_fields__["SURFACE"].metadata['interlis']['meta_attributes']
                                layer = QgsVectorLayer(
                                    f"Polygon?crs={meta_attributes.get('CRS') or 'EPSG:2056'}", layer_name, "memory"
                                )
                                self.qgis_ili_layer_registry[oid][layer_name] = layer
                                QgsProject.instance().addMapLayer(layer)

                                # connect to function
                                layer.selectionChanged.connect(on_selection_changed)
                            else:
                                layer = self.qgis_ili_layer_registry[oid][layer_name]
                            if layer_name not in qgis_feature_batches[oid]:
                                qgis_feature_batches[oid][layer_name] = []
                            feature_batch = qgis_feature_batches[oid][layer_name]
                            pr = layer.dataProvider()
                            pr.addAttributes([
                                QgsField("uuid", QVariant.String)
                            ])
                            layer.updateFields()
                            for attribute_name, polygon in geom_polygon_values:
                                f = QgsFeature(layer.fields())
                                boundaries = []
                                for boundary in polygon.SURFACE.BOUNDARY:
                                    ring = []
                                    for vertex in boundary.POLYLINE.vertices:
                                        ring.append(QgsPointXY(vertex.C1, vertex.C2))
                                    boundaries.append(ring)
                                f.setGeometry(QgsGeometry.fromPolygonXY(boundaries))
                                f["uuid"] = str(uuid.uuid4())
                                feature_batch.append(f)
                                self.feature_linker[f["uuid"]] = obj
        for oid_key in qgis_feature_batches:
            for layer_name_key in qgis_feature_batches[oid_key]:
                layer = self.qgis_ili_layer_registry[oid_key][layer_name_key]
                features = qgis_feature_batches[oid_key][layer_name_key]
                print(f"  Adding {len(features)} features to {layer_name_key}")
                pr = layer.dataProvider()
                pr.addFeatures(features)
                layer.updateExtents()
                QCoreApplication.processEvents()
                iface.mapCanvas().setExtent(layer.extent())
                iface.mapCanvas().refreshAllLayers()
                time.sleep(0.1)
        self._process_batch = []


parser_config = ParserConfig(
    fail_on_unknown_properties=False,
    fail_on_unknown_attributes=False,
)
with temp_register():
    parser = IndexXmlParser(parser_config)
    data = parser.parse(xtf_path, Transfer)


    def on_link_clicked(url):
        # url ist ein QUrl-Objekt
        url_string = url.toString()
        url_parts = url_string.split(':')
        if ':'.join([url_parts[0], url_parts[1]]) == "aktion:info":
            parser.render_result([(parser.transfer_element_index[url_parts[-2]][url_parts[-1]], url_parts[-2])])
    text_browser.anchorClicked.connect(on_link_clicked)
