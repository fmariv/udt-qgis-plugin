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

# TODO log, continue testing and enhancing the module


class CartographicDocument:
    """ Cartographic document generation class """

    def __init__(self, line_id, scale, generate_pdf, input_layers=None):
        # Initialize instance attributes
        # Set environment variables
        self.line_id = line_id
        self.scale = scale
        self.generate_pdf = generate_pdf
        self.input_layers = input_layers
        # Common
        self.current_date = datetime.now().strftime("%Y/%m/%d")
        self.project = QgsProject.instance()
        self.arr_lines_data = np.genfromtxt(LAYOUT_LINE_DATA, dtype=None, encoding='utf-8-sig', delimiter=';', names=True)
        self.layout_manager = self.project.layoutManager()
        # Input dependant
        self.proposta_2_exists = self.check_proposta_2_exists()
        # The scale determines the layout to generate
        self.layout_name = self.get_layout_name()
        self.layout = self.layout_manager.layoutByName(self.layout_name)
        # The number of input layers passed as variable determines the legend of the cartographic document, due
        # it means if there are multiple proposals from both councils
        self.legend = self.set_legend()
        self.muni_1_nomens, self.muni_2_nomens = None, None
        self.muni_1_normalized_name, self.muni_2_normalized_name = None, None
        self.dissolve_temp, self.split_temp = None, None  # temporal layers
        self.atlas = None
        # Inpunt non dependant
        self.string_date = None
        # Set input layers if necessary
        self.set_input_layers()

    # #######################
    # Set up the environment
    def check_proposta_2_exists(self):
        """  """
        # Check if exists any of the second council proposal layers
        if len(self.project.mapLayersByName('Punt Delimitació 2')) != 0 or len(
                self.project.mapLayersByName('Lin Tram Proposta 2')) != 0:
            return True
        # Check if the user has passed any input layer as variable
        if self.input_layers:
            n_input_layers = len(self.input_layers)
            if n_input_layers == 6:
                return True

    def set_input_layers(self):
        """  """
        if self.input_layers:
            self.point_rep_layer = QgsVectorLayer(self.input_layers[0], 'Punt Replantejament')
            self.lin_tram_rep_layer = QgsVectorLayer(self.input_layers[1], 'Lin Tram')
            self.point_del_layer = QgsVectorLayer(self.input_layers[2], 'Punt Delimitació')
            self.lin_tram_ppta_del_layer = QgsVectorLayer(self.input_layers[3], 'Lin Tram Proposta')
            # Set second council's proposal layers if necessary
            if self.proposta_2_exists:
                self.point_del_layer_2 = QgsVectorLayer(self.input_layers[4], 'Punt Delimitació 2')
                self.lin_tram_ppta_del_layer_2 = QgsVectorLayer(self.input_layers[5], 'Lin Tram Proposta 2')
                self.new_vector_layers = (self.lin_tram_rep_layer, self.lin_tram_ppta_del_layer_2,
                                          self.lin_tram_ppta_del_layer, self.point_rep_layer, self.point_del_layer_2,
                                          self.point_del_layer)
            else:
                self.new_vector_layers = (self.lin_tram_rep_layer,self.lin_tram_ppta_del_layer,
                                          self.point_rep_layer, self.point_del_layer)

    def set_legend(self):
        """  """
        if self.proposta_2_exists:
            legend = self.layout_manager.layoutByName(LLEGENDA[2])
        else:
            legend = self.layout_manager.layoutByName(LLEGENDA[1])

        return legend

    def get_layout_name(self):
        """  """
        layout = None
        if self.scale == '1:5 000':
            layout = ESCALA[1]
        elif self.scale == '1:2 500':
            layout = ESCALA[2]

        return layout

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
            # TODO refactor this part
            self.muni_1_normalized_name, self.muni_2_normalized_name = self.get_municipis_normalized_names()
            self.dissolve_lin_tram_ppta()
            self.split_dissolved_layer()
            self.sort_splitted_layer()
            self.set_up_atlas()
            self.export_atlas()
            self.export_legend()
            self.image_to_pdf()
            self.rm_split_map_layer()
            self.rm_temp()

    # ##########
    # Get variables
    def get_municipis_nomens(self):
        """  """
        muni_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == int(self.line_id))][0]
        muni_1_nomens = muni_data[3]
        muni_2_nomens = muni_data[4]

        return muni_1_nomens, muni_2_nomens

    def get_municipis_normalized_names(self):
        """  """
        muni_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == int(self.line_id))][0]
        muni_1_name = muni_data[1]
        muni_2_name = muni_data[2]
        # Normalize the names
        muni_1_normalized_name = muni_1_name.replace("'", "").replace(" ", "-").upper()
        muni_2_normalized_name = muni_2_name.replace("'", "").replace(" ", "-").upper()

        return muni_1_normalized_name, muni_2_normalized_name

    def get_string_date(self):
        """  """
        date_splitted = self.current_date.split('/')
        day = date_splitted[-1]
        if day[0] == '0':
            day = day[1]
        year = date_splitted[0]
        month = MESOS_CAT[date_splitted[1]]
        string_date = f'{day} {month} {year} '

        return string_date

    # ##########
    # Edit labels
    def edit_ref_label(self):
        """  """
        ref_layout = self.layout.itemById('Ref')
        ref_legend = self.legend.itemById('Title')

        ref_layout.setText(f"Document cartogràfic referent a l'acta de les operacions de delimitació entre els "
                           f"termes municipals {self.muni_1_nomens} i {self.muni_2_nomens}.")
        ref_legend.setText(f"DOCUMENT CARTOGRÀFIC REFERENT A L'ACTA DE LES OPERACIONS DE DELIMITACIÓ ENTRE ELS "
                           f"TERMES MUNICIPALS {self.muni_1_nomens.upper()} I {self.muni_2_nomens.upper()}.")

    def edit_date_label(self):
        """  """
        date_layout = self.layout.itemById('Date')
        date_legend = self.legend.itemById('Date')

        if self.scale == '1:2 500':
            layout_date = f'{self.string_date} (Base topogràfica de treball a escala 1:1 000)'
        else:
            layout_date = self.string_date

        date_layout.setText(layout_date)
        date_legend.setText(f'Data: {self.string_date}')

    # #######################
    # Update the map layers
    def update_map_layers(self):
        """  """
        self.rm_map_layers()
        self.add_map_layers()
        self.add_layers_styles()

    def rm_map_layers(self):
        """  """
        layers = self.project.mapLayers().values()
        for layer in layers:
            if layer.name() != 'Termes municipals' and layer.name() != 'Color orthophoto' and 'llegenda' not in layer.name():
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

            if self.proposta_2_exists:
                if layer.name() == 'Punt Delimitació 2':
                    layer.loadNamedStyle(os.path.join(LAYOUT_DOC_CARTO_STYLE_DIR, 'fites_delimitacio_2.qml'))
                    layer.triggerRepaint()
                elif layer.name() == 'Lin Tram Proposta 2':
                    layer.loadNamedStyle(os.path.join(LAYOUT_DOC_CARTO_STYLE_DIR, 'linia_terme_delimitacio_2.qml'))
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
        # Set the segment split length depending on the layout scale
        length = None
        if self.scale == '1:5 000':
            length = 1500
        elif self.scale == '1:2 500':
            length = 750
        parameters = {'input': self.dissolve_temp, 'length': length, 'units': 1,
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

        # TODO not null
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
        self.atlas = self.layout.atlas()
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

    def get_pdf_file_name(self):
        """  """
        date = datetime.now().strftime("%Y%m%d")
        pdf_file_name = f'DCD_{self.line_id}_{date}_{self.muni_1_normalized_name}_{self.muni_2_normalized_name}.pdf'

        return pdf_file_name

    def image_to_pdf(self):
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
        # Merge all the images in a single PDF file
        pdf_file_name = self.get_pdf_file_name()
        img1.save(os.path.join(LAYOUT_OUTPUT, pdf_file_name), save_all=True, append_images=img_list)
        # Close the images to avoid background processes that can lock the files
        img1.close()
        for i in img_list:
            i.close()

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

    # #######################
    # Remove temporal files and reset environment
    def rm_split_map_layer(self):
        """  """
        self.project.removeMapLayer(self.split_temp)

    @staticmethod
    def rm_temp():
        """  """
        for filename in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, filename)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                pass
