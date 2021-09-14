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
import re
from datetime import datetime
import os
from PIL import Image

from ..config import *

from qgis.core import (QgsVectorLayer,
                       QgsVectorFileWriter,
                       QgsCoordinateReferenceSystem,
                       QgsField,
                       QgsFeature,
                       QgsGeometry,
                       QgsProject,
                       QgsMessageLog,
                       QgsWkbTypes,
                       QgsFillSymbol,
                       QgsLayoutExporter)
from PyQt5.QtCore import QVariant
from qgis.core.additions.edit import edit

import processing
from processing.algs.grass7.Grass7Utils import Grass7Utils
# Ensure that the GRASS 7 folder is correctly configured
Grass7Utils.path = GRASS_LOCAL_PATH

# TODO tener en cuenta la posibilidad de que hayan 2 propuestas de los ayuntamientos
# TODO log


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
        self.layout = self.layout_manager.layoutByName('Document cartografic 1:5000 - comparatiu')   # TODO hacerlo dependiente del input del usuario
        self.legend = self.layout_manager.layoutByName('Llegenda - comparatiu')  # TODO hacerlo dependiente del input del usuario
        self.arr_lines_data = np.genfromtxt(LAYOUT_LINE_DATA, dtype=None, encoding='utf-8-sig', delimiter=';', names=True)
        # Inpunt non dependant
        self.string_date = None
        # Input dependant
        self.muni_1_nomens, self.muni_2_nomens = None, None
        self.dissolve_temp, self.split_temp = None, None   # temporal layers
        self.atlas = None
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
            self.sort_splitted_layer()
            self.set_up_atlas()
            self.export_atlas()
            self.export_legend()
            self.image_to_pdf()

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
                layer.loadNamedStyle(os.path.join(LAYOUT_DOC_CARTO_STYLE_DIR, 'fites_delimitacio_1.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'Punt Replantejament':
                layer.loadNamedStyle(os.path.join(LAYOUT_DOC_CARTO_STYLE_DIR, 'fites_replantejament.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'Lin Tram Proposta':
                layer.loadNamedStyle(os.path.join(LAYOUT_DOC_CARTO_STYLE_DIR, 'linia_terme_delimitacio_1.qml'))
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

    def sort_splitted_layer(self):
        """ """
        # Get the first point geometry in order to check whether a line segment intersects it's geometry or not,
        # which imposes how to sort the line segments
        first_point = self.get_first_point()
        # Add sort field to the split layer
        self.add_field_split_layer()
        # Check intersection and calculate the sort field
        with edit(self.split_temp):
            first_check_done = False
            for feat in self.split_temp.getFeatures():
                # Check the first segment in order to know if the sort must be ascending or descending
                if not first_check_done:
                    if feat.geometry().buffer(10, 5).intersects(first_point):
                        feat['Sort'] = 1
                        n = 1
                        sort_desc = True
                    else:
                        feat['Sort'] = self.split_temp.featureCount()
                        n = self.split_temp.featureCount()
                        sort_desc = False
                    first_check_done = True
                    self.split_temp.updateFeature(feat)
                    continue
                else:
                    if sort_desc:
                        n += 1
                    else:
                        n -= 1
                    feat['Sort'] = n
                    self.split_temp.updateFeature(feat)

    def get_first_point(self):
        """  """
        point_del_layer = self.project.mapLayersByName('Punt Delimitació')[0]
        for point in point_del_layer.getFeatures():
            point_num = re.findall(r"\d+", point['ETIQUETA'])[0]
            if point_num == '1':
                point_geom = point.geometry()

        # TODO controlar que no pueda ser nulo
        return point_geom

    def add_field_split_layer(self):
        """  """
        sort_field = QgsField('Sort', QVariant.Int)
        self.split_temp.dataProvider().addAttributes([sort_field])
        self.split_temp.updateFields()

    def set_up_atlas(self):
        """  """
        # Set and add the coverage layer that the atlas must follow, which is the splitted line
        self.add_coverage_layer()
        # Set the atlas config
        manager = self.project.layoutManager()
        layout = manager.layoutByName('Document cartografic 1:5000 - comparatiu')   # TODO hacer dependiente de la escala
        self.atlas = layout.atlas()
        self.config_atlas()

    def add_coverage_layer(self):
        """  """
        layer_transparency = self.get_symbol({'color': '255,0,0,0'})
        self.split_temp.renderer().setSymbol(layer_transparency)
        self.split_temp.triggerRepaint()
        self.project.addMapLayer(self.split_temp)

    def config_atlas(self):
        """  """
        self.atlas.setEnabled(True)
        self.atlas.setCoverageLayer(self.split_temp)
        self.atlas.setHideCoverage(True)
        self.atlas.setSortFeatures(True)
        self.atlas.setSortExpression("Sort")
        self.atlas.setFilterFeatures(True)

    def export_legend(self):
        """  """
        export = QgsLayoutExporter(self.legend)
        export.exportToImage(os.path.join(TEMP_DIR, 'legend.jpg'), QgsLayoutExporter.ImageExportSettings())

    def export_atlas(self):
        """  """
        self.atlas.beginRender()
        self.atlas.first()

        # TODO comprovar si la linia cabe en un solo layout

        for i in range(0, self.atlas.count()):
            # Creata a exporter Layout for each layout generate with Atlas
            exporter = QgsLayoutExporter(self.atlas.layout())
            # TODO log this
            print('Saving File: ' + str(self.atlas.currentFeatureNumber()) + ' of ' + str(self.atlas.count()))
            exporter.exportToImage(os.path.join(TEMP_DIR, f'{self.atlas.currentFilename()}.jpg'),
                                   QgsLayoutExporter.ImageExportSettings())
            # Show which file is creating
            print('Create File: ' + self.atlas.currentFilename())
            # Create Next Layout
            self.atlas.next()

        # Close Atlas Creation
        self.atlas.endRender()

    @staticmethod
    def image_to_pdf():
        """ """
        # First get a list with the path of the JPG files
        jpg_list = []
        # Append the legend as the first item in the JPG files
        legend_path = os.path.join(TEMP_DIR, 'legend.jpg')
        if os.path.exists(legend_path):
            jpg_list.append(legend_path)
        # Append the rest of the JPG files
        for root, dirs, files in os.walk(TEMP_DIR):
            for f in files:
                f_path = os.path.join(root, f)
                if f.endswith('.jpg') and f_path not in jpg_list:
                    jpg_list.append(f_path)

        # Open the first JPG file (legend) as PIL image
        img1 = Image.open(jpg_list[0])
        # Open the res of JPG files as PIL images and append to a PIL image list
        img_list = []
        for img in jpg_list[1:]:
            img_list.append(Image.open(img))

        img1.save(os.path.join(TEMP_DIR, 'test.pdf'), save_all=True, append_images=img_list)
        img1.close()

    @staticmethod
    def get_symbol(style):
        """  """
        return QgsFillSymbol.createSimple(style)

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
