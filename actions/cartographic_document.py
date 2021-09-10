# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the CartographicDocument class is defined. The main function
of this class is to run the automation process that edits a boundary line's layout and
generates or not that layout as a pdf document.
***************************************************************************/
"""

import numpy as np
from datetime import datetime
import os

import processing
from qgis.core import (QgsVectorLayer,
                       QgsVectorFileWriter,
                       QgsCoordinateReferenceSystem,
                       QgsField,
                       QgsFeature,
                       QgsGeometry,
                       QgsProject,
                       QgsMessageLog,
                       QgsWkbTypes,
                       QgsFillSymbol)

from PyQt5.QtWidgets import QMessageBox

from ..config import *

# TODO Workflow: dissolver linia, splitear con grass v.split
# TODO algoritmo para ordenar las línias...


class CartographicDocument:
    """ Cartographic document generation class """

    def __init__(self, line_id, generate_pdf, input_layers=None):
        # Initialize instance attributes
        # Set environment variables
        self.line_id = line_id
        self.generate_pdf = generate_pdf
        # Common
        self.current_date = datetime.now().strftime("%Y/%m/%d")
        self.project = QgsProject.instance()
        self.layout_manager = self.project.layoutManager()
        self.layout = self.layout_manager.layoutByName('Document-cartografic-1:5000')   # TODO Hacerlo dependiente del input del usuario
        self.arr_lines_data = np.genfromtxt(LAYOUT_LINE_DATA, dtype=None, encoding='utf-8-sig', delimiter=';', names=True)
        # Inpunt non dependant
        self.string_date = None
        # Input dependant
        self.muni_1_nomens, self.muni_2_nomens = None, None
        self.dissolve_temp, self.split_temp = None, None   # temporal layers
        # Set input layers if necessary
        if input_layers:
            self.point_rep_layer = QgsVectorLayer(input_layers[0], 'Punt Replantejament')
            self.lin_tram_rep_layer = QgsVectorLayer(input_layers[1], 'Lin Tram')
            self.point_del_layer = QgsVectorLayer(input_layers[2], 'Punt Delimitació')
            self.lin_tram_ppta_del_layer = QgsVectorLayer(input_layers[3], 'Lin Tram Proposta')
            self.new_vector_layers = (self.lin_tram_rep_layer,self.lin_tram_ppta_del_layer,
                                      self.point_rep_layer, self.point_del_layer)

    # #######################
    # Generate the cartographic document
    def generate_doc_carto_layout(self):
        """  """
        # Get variables
        self.muni_1_nomens, self.muni_2_nomens = self.get_municipis_nomens()
        self.string_date = self.get_string_date()
        # Edit layout labels
        self.edit_ref_label()
        self.edit_date_label()
        # Generate and export the Atlas as PDF if the user wants
        if self.generate_pdf:
            self.dissolve_lin_tram_ppta()
            self.split_dissolved_layer()
            self.manage_atlas()
            # TODO generar Atlas
            # 1. Seleccionar layout
            # 2. Seleccionar linea segmentada y que no se vea
            # 3. Exportar atlas

    # ##########
    # Get variables
    def get_municipis_nomens(self):
        """  """
        muni_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == int(self.line_id))][0]
        muni_1_nomens = muni_data[3]
        muni_2_nomens = muni_data[4]

        return muni_1_nomens, muni_2_nomens

    def get_string_date(self):
        """  """
        date_splitted = self.current_date.split('/')
        day = date_splitted[-1]
        if day[0] == '0':
            day = day[1]
        year = date_splitted[0]
        month = MESOS_CAT[date_splitted[1]]
        string_date = f'{day} {month} {year}'

        return string_date

    # ##########
    # Edit labels
    def edit_ref_label(self):
        """  """
        ref = self.layout.itemById('Ref')
        ref.setText(f"Document cartogràfic referent a l'acta de les operacions de delimitació entre els "
                    f"termes municipals {self.muni_1_nomens} i {self.muni_2_nomens}.")

    def edit_date_label(self):
        """  """
        date = self.layout.itemById('Date')
        date.setText(self.string_date)

    # #######################
    # Update the map layers
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

    # #######################
    # Generate atlas
    def dissolve_lin_tram_ppta(self):
        """  """
        lin_tram_ppta = self.project.mapLayersByName('Lin Tram Proposta')[0]
        parameters = {'INPUT': lin_tram_ppta, 'OUTPUT': os.path.join(TEMP_DIR, 'doc-carto_dissolve_temp.shp')}
        processing.run("native:dissolve", parameters)
        # Set the layer as class variable
        self.dissolve_temp = QgsVectorLayer(os.path.join(TEMP_DIR, 'doc-carto_dissolve_temp.shp'), 'dissolve-temp', 'ogr')

    def split_dissolved_layer(self):
        """  """
        parameters = {'input': self.dissolve_temp, 'length': 1500, 'units': 1,
                      'output': os.path.join(TEMP_DIR, 'doc-carto_split_temp.shp')}
        processing.run("grass7:v.split", parameters)
        self.split_temp = QgsVectorLayer(os.path.join(TEMP_DIR, 'doc-carto_split_temp.shp'), 'split-temp', 'ogr')

    def manage_atlas(self):
        """  """
        # TODO meter esto en una funcion aparte
        layer_transparency = self.get_symbol({'color': '255,0,0,0'})
        self.split_temp.renderer().setSymbol(layer_transparency)
        self.split_temp.triggerRepaint()
        self.project.addMapLayer(self.split_temp)

    @staticmethod
    def get_symbol(style):
        """  """
        return QgsFillSymbol.createSimple({style})

    # #######################
    # Validators
    def validate_geometry_layers(self):
        """  """
        # Validate points
        if self.point_del_layer.wkbType() != QgsWkbTypes.PointZ or self.point_rep_layer.wkbType() != QgsWkbTypes.PointZ:
            return False
        # Validate lines
        if self.lin_tram_rep_layer.wkbType() != QgsWkbTypes.MultiLineString or self.lin_tram_ppta_del_layer.wkbType() != QgsWkbTypes.MultiLineString:
            return False

        return True
