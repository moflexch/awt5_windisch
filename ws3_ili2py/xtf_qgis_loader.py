import base64
import logging
from dataclasses import fields
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QVariant
from ili2py_interface.references import BinBlBoxType, Ref
from xtf_read import read

logging.getLogger().setLevel(logging.DEBUG)

class InfoWindow(QtWidgets.QDialog):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("XTF-Browser")
        self.resize(400, 300)
        self.text_browser = QtWidgets.QTextBrowser(self)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.text_browser)
        self.setLayout(self.layout)
        self.resizeEvent = self.on_resize


    def on_resize(self, event):
        return super(QtWidgets.QDialog, self).resizeEvent(event)


def load(xtf_path: str):
    parser, data = read(xtf_path)
    qgis_ili_layer_registry = {}
    info_window = InfoWindow()

    def render_result(ili_objects):
        feature_texts = []
        for ili_object, layer_name in ili_objects:
            feature_text = [
                f'<p><h2>{layer_name}</h2><table style="width:100%; border:1px solid #555; border-collapse:collapse;">'
            ]
            for field in fields(ili_object):
                name = field.name
                if name not in ili_object.geom_attributes:
                    value = getattr(ili_object, name)
                    if isinstance(value, Ref):
                        feature_text.append(
                            f'<tr><td>{name}</td><td><a href="aktion:info:{field.metadata["interlis"]["reference_targets"][0]}:{value.ref}">{value}</a></td></tr>'
                        )
                    elif isinstance(value, BinBlBoxType):
                        feature_text.append(
                            f'<tr><td style="width:200px; text-align:center; vertical-align:middle;">{name}</td><td><img style="width:100%; height:auto;" src="data:image/png;base64,{base64.b64encode(value.BINBLBOX).decode("ascii")}"></td></tr>'
                        )
                    else:
                        feature_text.append(
                            f'<tr><td style="padding:10px;">{name}</td><td>{value}</td></tr>'
                        )
            feature_text.append("</table></p>")
            feature_texts.append("\n".join(feature_text))
            info_window.text_browser.setHtml(f"""
                        <h1>Selektierte Elemente:</h1>
                        {"\n".join(feature_texts)}
                        """)
        info_window.show()

    def on_selection_changed(selected, deselected, clear_and_select):
        ili_objects = []
        for oid_key in qgis_ili_layer_registry:
            for layer_name_key in qgis_ili_layer_registry[oid_key]:
                layer = qgis_ili_layer_registry[oid_key][layer_name_key]
                selected_features = layer.selectedFeatures()
                for feature in selected_features:
                    ili_object = parser.transfer_element_index[oid_key][feature["tid"]]
                    ili_objects.append((ili_object, layer_name_key))
        render_result(ili_objects)

    def on_link_clicked(url):
        # url ist ein QUrl-Objekt
        url_string = url.toString()
        url_parts = url_string.split(":")
        if ":".join([url_parts[0], url_parts[1]]) == "aktion:info":
            render_result(
                [
                    (
                        parser.transfer_element_index[url_parts[-2]][url_parts[-1]],
                        url_parts[-2],
                    )
                ]
            )

    def fetch_layer(layer_name, oid, qgis_layer_type):
        if layer_name not in qgis_ili_layer_registry[oid]:
            # layer did not exist jet, we create it and add it to the layer-dict
            layer = QgsVectorLayer(
                qgis_layer_type,
                layer_name,
                "memory",
            )
            qgis_ili_layer_registry[oid][layer_name] = layer
            QgsProject.instance().addMapLayer(layer)
            # connect to function
            layer.selectionChanged.connect(on_selection_changed)
        else:
            layer = qgis_ili_layer_registry[oid][layer_name]
        return layer

    def qgis_stuff():
        for oid in parser.geometric_classes_index:
            for geometry_type in parser.geometric_classes_index[oid]:
                if len(list(parser.geometric_classes_index[oid][geometry_type].keys())) > 0:
                    qgis_ili_layer_registry[oid] = {}
                    layer_name = f"{oid}-{geometry_type}"
                    layer = fetch_layer(layer_name, oid, f"{geometry_type}?crs=EPSG:2056")
                    pr = layer.dataProvider()
                    pr.addAttributes([QgsField("tid", QVariant.String)])
                    layer.updateFields()
                    if geometry_type == parser.point_type:
                        feature_batch = []
                        for tid in parser.geometric_classes_index[oid][geometry_type]:
                            for attribute_name, geometry in parser.geometric_classes_index[oid][geometry_type][tid]:
                                if geometry:
                                    f = QgsFeature(layer.fields())
                                    f.setGeometry(
                                        QgsGeometry.fromPointXY(
                                            QgsPointXY(geometry.coord.C1, geometry.coord.C2)
                                        )
                                    )
                                    f["tid"] = tid
                                    feature_batch.append(f)
                        pr.addFeatures(feature_batch)
                    elif geometry_type == parser.line_type:
                        pass
                    elif geometry_type == parser.polygon_type:
                        feature_batch = []
                        for tid in parser.geometric_classes_index[oid][geometry_type]:
                            for attribute_name, geometry in parser.geometric_classes_index[oid][geometry_type][tid]:
                                if geometry:
                                    f = QgsFeature(layer.fields())
                                    boundaries = []
                                    for boundary in geometry.SURFACE.BOUNDARY:
                                        ring = []
                                        for vertex in boundary.POLYLINE.vertices:
                                            ring.append(QgsPointXY(vertex.C1, vertex.C2))
                                        boundaries.append(ring)
                                    f.setGeometry(QgsGeometry.fromPolygonXY(boundaries))
                                    f["tid"] = tid
                                    feature_batch.append(f)
                        pr.addFeatures(feature_batch)

    info_window.text_browser.anchorClicked.connect(on_link_clicked)
    qgis_stuff()

load("/home/kalle/projects/rudert-geoinformatik/ili2py/tests/data/models/OeREBKRMtrsfr_V2_0/ch.bazl.kataster-belasteter-standorte-zivilflugplaetze_v2_0.oereb.xtf")
