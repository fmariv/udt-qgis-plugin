# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the CartographicDocument class is defined. The main function
of this class is to run the automation process that edits a boundary line's layout and
generates or not that layout as a pdf document.
***************************************************************************/
"""

from datetime import datetime
import os
import shutil

from qgis.core import (QgsVectorLayer,
                       QgsVectorFileWriter,
                       QgsCoordinateReferenceSystem,
                       QgsField,
                       QgsFeature,
                       QgsGeometry,
                       QgsProject,
                       QgsMessageLog)
from qgis.core.additions.edit import edit
from PyQt5.QtWidgets import QMessageBox

from ..config import *

# TODO añadir control de tipo de geometria


class CartographicDocument:
    """ Cartographic document generation class """

    def __init__(self, line_id, generate_pdf, input_layers=None):
        # Initialize instance attributes
        # Common
        self.current_date = datetime.now().strftime("%Y%m%d")
        self.project = QgsProject.instance()
        # Set environment variables
        self.line_id = line_id
        self.generate_pdf = generate_pdf
        # Set input layers if necessary
        if input_layers:
            self.point_rep_layer = QgsVectorLayer(input_layers[0], 'Punt Replantejament')
            self.lin_tram_rep_layer = QgsVectorLayer(input_layers[1], 'Lin Tram')
            self.point_del_layer = QgsVectorLayer(input_layers[2], 'Punt Delimitació')
            self.lin_tram_ppta_del_layer = QgsVectorLayer(input_layers[3], 'Lin Tram Proposta')
            self.new_vector_layers = (self.lin_tram_rep_layer,self.lin_tram_ppta_del_layer, self.point_rep_layer, self.point_del_layer)

    def generate_doc_carto_layout(self):
        """  """
        pass

    def update_map_layers(self):
        """  """
        self.remove_map_layers()
        self.add_map_layers()
        self.add_layers_styles()

    def remove_map_layers(self):
        """  """
        layers = self.project.mapLayers().values()
        for layer in layers:
            if layer.name() != 'Termes municipals' and layer.name() != 'Color orthophoto':
                self.project.removeMapLayer(layer)

    def add_map_layers(self):
        """  """
        for layer in self.new_vector_layers:
            self.project.addMapLayer(layer)

    def add_layers_styles(self):
        """  """
        layers = self.project.mapLayers().values()
        for layer in layers:
            if layer.name() == 'Punt Delimitació':
                layer.loadNamedStyle(os.path.join(LAYOUT_DOC_CARTO_STYLE_DIR, 'fites_delimitacio.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'Punt Replantejament':
                layer.loadNamedStyle(os.path.join(LAYOUT_DOC_CARTO_STYLE_DIR, 'fites_replantejament.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'Lin Tram Proposta':
                layer.loadNamedStyle(os.path.join(LAYOUT_DOC_CARTO_STYLE_DIR, 'linia_terme_delimitacio.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'Lin Tram':
                layer.loadNamedStyle(os.path.join(LAYOUT_DOC_CARTO_STYLE_DIR, 'linia_terme_replantejament.qml'))
                layer.triggerRepaint()
