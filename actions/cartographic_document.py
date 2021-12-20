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
import os
from PIL import Image

from ..config import *

from qgis.core import (QgsVectorLayer,
                       QgsCoordinateReferenceSystem,
                       QgsField,
                       QgsGeometry,
                       QgsProject,
                       QgsMessageLog,
                       QgsWkbTypes,
                       QgsFillSymbol,
                       QgsLayoutExporter,
                       QgsMessageLog,
                       Qgis)
from PyQt5.QtCore import QVariant
from qgis.core.additions.edit import edit

import processing
from processing.algs.grass7.Grass7Utils import Grass7Utils
# Ensure that the GRASS 7 folder is correctly configured
# Grass7Utils.path = GRASS_LOCAL_PATH


class CartographicDocument:
    """ Cartographic document generation class """

    def __init__(self,
                 line_id,
                 date,
                 scale,
                 generate_pdf,
                 update_labels,
                 input_layers=None):
        """
        Constructor

        :param line_id: ID of the line to generate the Cartographic document
        :type line_id: str

        :param date: Date to write in the layout
        :type date: QgsDate

        :param scale: Scale of the layout
        :type scale: str

        :param generate_pdf: Indicates whether the user wants to generate the pdf file or not
        :type generate_pdf: bool

        :param update_labels: Indicates whether the user wants to update the layout's labels or not
        :type generate_pdf: bool

        :param input_layers: List with the input layers to use in order to generate the document
        :type input_layers: tuple
        """
        # Initialize instance attributes
        # Set environment variables
        self.line_id = line_id
        self.date = date
        self.scale = scale
        self.generate_pdf = generate_pdf
        self.update_labels = update_labels
        self.input_layers = input_layers
        self.log_environment_variables()
        # Common
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
        self.muni_1_name, self.muni_2_name = None, None
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
        """
        Check if exists proposal layers from the 2n council or not, which determines the legend, layers
        styles to use

        :return Indicates if the Cartographic document has 2 proposals from every municipality council or not
        :rtype bool
        """
        # Check if the user has passed any input layer as variable
        if self.input_layers:
            n_input_layers = len(self.input_layers)
            if n_input_layers == 6:
                QgsMessageLog.logMessage('El DCD contempla la proposta de dos ajuntaments', level=Qgis.Info)
                return True
            elif n_input_layers == 4:
                QgsMessageLog.logMessage('El DCD NO contempla la proposta de dos ajuntaments', level=Qgis.Info)
                return False
        # Check if exists any of the second council proposal layers
        if len(self.project.mapLayersByName('Punt Delimitació 2')) != 0 or len(
                self.project.mapLayersByName('Lin Tram Proposta 2')) != 0:
            QgsMessageLog.logMessage('El DCD contempla la proposta de dos ajuntaments', level=Qgis.Info)
            return True

    def set_input_layers(self):
        """ Set as vector layers the layers passed as input to the class """
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
        """
        Set the legend layout depending on whether exists proposals from the 2n council or not

        :return legend: Layout that works as legend that has to be appended to the document
        :rtype: QgsLayout
        """
        if self.proposta_2_exists:
            legend = self.layout_manager.layoutByName(LLEGENDA[2])
        else:
            legend = self.layout_manager.layoutByName(LLEGENDA[1])

        return legend

    def get_layout_name(self):
        """
        Get the map layout name depending on the scale

        :return layout: Layout name
        :rtype: str
        """
        layout = None
        if self.scale == '1:5 000':
            layout = ESCALA[1]
        elif self.scale == '1:2 500':
            layout = ESCALA[2]

        return layout

    def log_environment_variables(self):
        """ Log as a MessageLog the environment variables of the DCD """
        QgsMessageLog.logMessage(f'ID Linia: {self.line_id}', level=Qgis.Info)
        QgsMessageLog.logMessage(f'Escala del DCD: {self.scale}', level=Qgis.Info)
        pdf = 'Si' if self.generate_pdf else 'No'
        QgsMessageLog.logMessage(f'Generar PDF: {pdf}', level=Qgis.Info)
        update_labels = 'Si' if self.update_labels else 'No'
        QgsMessageLog.logMessage(f'Actualitzar etiquetes: {update_labels}', level=Qgis.Info)
        update_layers = 'Si' if self.input_layers else 'No'
        QgsMessageLog.logMessage(f"Actualitzar capes: {update_layers}", level=Qgis.Info)

    # #######################
    # Generate the cartographic document
    def generate_doc_carto_layout(self):
        """
        Main entry point. Generates the cartographic document, only editing the map layout or even exporting
        it as a pdf file, depending on the user's input
        """
        QgsMessageLog.logMessage('Procés iniciat: generació de Document Cartogràfic de Referència', level=Qgis.Info)
        # Get variables
        self.muni_1_name, self.muni_2_name = self.get_municipalities_names()
        self.muni_1_nomens, self.muni_2_nomens = self.get_municipalities_nomens()
        self.string_date = self.get_string_date()
        # Edit layout labels
        if self.update_labels:
            QgsMessageLog.logMessage('Editant etiquetes de la composició...', level=Qgis.Info)
            self.edit_ref_label()
            self.edit_date_label()
            self.edit_scale_label()
            QgsMessageLog.logMessage('Etiquetes de la composició editades', level=Qgis.Info)
        # Generate and export the Atlas as PDF if the user wants
        if self.generate_pdf:
            QgsMessageLog.logMessage("Generant l'arxiu del Document Cartogràfic en format pdf...", level=Qgis.Info)
            # Get the normalized municipalities names, as needed for the output file name
            self.muni_1_normalized_name, self.muni_2_normalized_name = self.get_municipalities_normalized_names()
            # Create, manage and add to the map the atlas coverage layer
            self.manage_coverage_layer()
            # Set up, export and merge into a single pdf file the Cartographic document
            self.export_cartographic_doc()
            QgsMessageLog.logMessage('Procés finalitzat: Document Cartogràfic de Referència generat', level=Qgis.Info)
            # Reset the environment, removing the coverage layer from the map canvas and the temporal files
            self.reset_environment()

    # ##########
    # Get variables
    def get_municipalities_names(self):
        """
        Get the municipalities names

        :return: muni_1_name: Name of the first municipality
        :rtype: str

        :return: muni_2_name: Name of the second municipality
        :rtype: str
        """
        muni_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == int(self.line_id))][0]
        muni_1_name = muni_data[1]
        muni_2_name = muni_data[2]

        QgsMessageLog.logMessage(f'Nom dels municipis: {muni_1_name}, {muni_2_name}', level=Qgis.Info)

        return muni_1_name, muni_2_name

    def get_municipalities_nomens(self):
        """
        Get the way to name the municipalities

        :return: muni_1_nomens: Way to name the first municipality
        :rtype: str

        :return: muni_2_nomens: Way to name the second municipality
        :stype: str
        """
        muni_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == int(self.line_id))][0]
        muni_1_nomens = muni_data[3]
        muni_2_nomens = muni_data[4]

        QgsMessageLog.logMessage(f'Nomenclatura dels municipis: {muni_1_nomens}, {muni_2_nomens}', level=Qgis.Info)

        return muni_1_nomens, muni_2_nomens

    def get_municipalities_normalized_names(self):
        """
        Get the normalized municipalities' names

        :return: muni_1_normalized_name: Normalized name of the first municipality
        rtype: str

        :return: muni_2_normalized_name: Normalized name of the second municipality
        rtype: str
        """
        muni_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == int(self.line_id))][0]
        muni_1_name = muni_data[1]
        muni_2_name = muni_data[2]
        # Normalize the names
        muni_1_normalized_name = muni_1_name.replace("'", "").replace(" ", "-").upper()
        muni_2_normalized_name = muni_2_name.replace("'", "").replace(" ", "-").upper()

        QgsMessageLog.logMessage(f'Noms normalitzats dels municipis: {muni_1_normalized_name}, {muni_2_normalized_name}', level=Qgis.Info)

        return muni_1_normalized_name, muni_2_normalized_name

    def get_string_date(self):
        """
        Get the current date as a string

        :return: string_date: Current date as string, with format [day month year]
        :rtype: str
        """
        current_date = self.date.strftime("%Y/%m/%d")
        date_splitted = current_date.split('/')
        day = date_splitted[-1]
        if day[0] == '0':
            day = day[1]
        year = date_splitted[0]
        month = MESOS_CAT[date_splitted[1]]
        string_date = f'{day} {month} {year}'

        QgsMessageLog.logMessage(f'Data de la delimitació: {string_date}', level=Qgis.Info)

        return string_date

    # ##########
    # Edit labels
    def edit_ref_label(self):
        """ Edit the reference and title labels from both map and legend layouts """
        ref_layout = self.layout.itemById('Ref')
        ref_legend = self.legend.itemById('Title')

        if not self.proposta_2_exists:
            ref_layout.setText(f"Document cartogràfic referent a l'acta de les operacions de delimitació entre els "
                               f"termes municipals {self.muni_1_nomens} i {self.muni_2_nomens}.")
            ref_legend.setText(f"DOCUMENT CARTOGRÀFIC REFERENT A L'ACTA DE LES OPERACIONS DE DELIMITACIÓ ENTRE ELS "
                               f"TERMES MUNICIPALS {self.muni_1_nomens.upper()} I {self.muni_2_nomens.upper()}.")
        else:
            ref_layout.setText(f"Document cartogràfic comparatiu entre la proposta de delimitació municipal "
                               f"entre els termes municipals {self.muni_1_nomens} i {self.muni_2_nomens} i la línia del replantejament.")
            ref_legend.setText(f"DOCUMENT CARTOGRÀFIC COMPARATIU ENTRE LA PROPOSTA DE DELIMITACIÓ MUNICIPAL "
                               f"ENTRE ELS TERMES MUNICIPALS {self.muni_1_nomens.upper()} I {self.muni_2_nomens.upper()} "
                               f"I LA LÍNIA DE REPLANTEJAMENT.")

    def edit_date_label(self):
        """ Edit the dates from both map and legend layouts """
        date_layout = self.layout.itemById('Date')
        date_legend = self.legend.itemById('Date')

        if self.scale == '1:2 500':
            layout_date = f'{self.string_date} (Base topogràfica de treball a escala 1:1 000)'
        else:
            layout_date = self.string_date

        date_layout.setText(layout_date)
        date_legend.setText(f'Data: {self.string_date}')

    def edit_scale_label(self):
        """ Edit the scale from the legend """
        scale_legend = self.legend.itemById('Scale')

        scale_legend.setText(f'Escala de representació {self.scale}')

    # #######################
    # Update the map layers
    def update_map_layers(self):
        """ Updates the map layers showed in the canvas, performing the following processes:
            - Remove all the unnecesary or old layers
            - Add the new layers to the canvas
            - Add style to the added layers
        """
        QgsMessageLog.logMessage('Actualitzant capes del mapa...')
        self.rm_map_layers()
        self.add_map_layers()
        self.add_layers_styles()
        QgsMessageLog.logMessage('Capes del mapa actualitzades')

    def rm_map_layers(self):
        """ Remove the unnecesary or old layers from the map canvas """
        layers = self.project.mapLayers().values()
        for layer in layers:
            if layer.name() != 'Termes municipals' and layer.name() != 'Color orthophoto' and 'llegenda' not in layer.name():
                self.project.removeMapLayer(layer)

    def add_map_layers(self):
        """ Add the new layers that the user has selected """
        for layer in self.new_vector_layers:
            self.project.addMapLayer(layer)

    def add_layers_styles(self):
        """ Add style and simbology to the added layers """
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
    def manage_coverage_layer(self):
        """
        Coverage layer generation's and managing entry point. The function involves the following processes:
            - Dissolve the first council line's proposal layer
            - Split the dissolved line
            - Sort the splitted line depending on where the first point is
        """
        self.dissolve_lin_tram_ppta()
        self.split_dissolved_layer()
        self.sort_splitted_layer()

    def dissolve_lin_tram_ppta(self):
        """
        Dissolve the first council proposal line, if it has more than one segment or is too long, in order to split
        it later
        """
        lin_tram_ppta = self.project.mapLayersByName('Lin Tram Proposta')[0]
        parameters = {'INPUT': lin_tram_ppta, 'OUTPUT': os.path.join(TEMP_DIR, f'doc-carto-{self.line_id}_dissolve_temp.shp')}
        processing.run("native:dissolve", parameters)
        # Set the layer as class variable
        self.dissolve_temp = QgsVectorLayer(os.path.join(TEMP_DIR, f'doc-carto-{self.line_id}_dissolve_temp.shp'),
                                            'dissolve-temp', 'ogr')

    def split_dissolved_layer(self):
        """
        Split the dissolved layer, in order to generate a coverage layer for the map atlas that covers the line
        by length and not by feature. The maximum split length deppends on the map scale
        """
        # Set the segment split length depending on the layout scale
        length = None
        if self.scale == '1:5 000':
            length = 1500
        elif self.scale == '1:2 500':
            length = 750
        parameters = {'input': self.dissolve_temp, 'length': length, 'units': 1,
                      'output': os.path.join(TEMP_DIR, f'doc-carto-{self.line_id}_split_temp.shp')}
        processing.run("grass7:v.split", parameters)
        self.split_temp = QgsVectorLayer(os.path.join(TEMP_DIR, f'doc-carto-{self.line_id}_split_temp.shp'),
                                         'split-temp', 'ogr')

    def sort_splitted_layer(self):
        """ Sort the splitted layer, in order to generate the map atlas in the correct segment order. To do that,
        the function performs the following processes:
            - Get the first point's geometry
            - Add a new sorting field to the splitted line
            - Buffer the splitted line and check if the first segment instersects with the first point's geometry.
              If it does, sorts the splitted line by descending order and, if not, by ascending order.
        """
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
        """
        Get the first point's geometry, in order to sort the splitted line

        :return: point_geom - First point's geometry as a QgsGeometry object
        :rtype: QgsGeometry
        """
        point_geom = None
        point_del_layer = self.project.mapLayersByName('Punt Delimitació')[0]
        for point in point_del_layer.getFeatures():
            point_num = re.findall(r"\d+", point['ETIQUETA'])[0]
            if point_num == '1':
                point_geom = point.geometry()

        if not point_geom:
            QgsMessageLog.logMessage('La primera fita no té una geometria vàlida', level=Qgis.Critical)

        return point_geom

    def add_field_split_layer(self):
        """ Add the sorting field to the splitted line """
        sort_field = QgsField('Sort', QVariant.Int)
        self.split_temp.dataProvider().addAttributes([sort_field])
        self.split_temp.updateFields()

    def set_up_atlas(self):
        """ Set up the map atlas, adding the coverage layer and loading it configuration """
        # Set and add the coverage layer that the atlas must follow, which is the splitted line
        self.add_coverage_layer()
        # Set the atlas config
        self.atlas = self.layout.atlas()
        self.config_atlas()

    def add_coverage_layer(self):
        """ Add the coverage layer to the atlas """
        layer_transparency = self.get_symbol({'color': '255,0,0,0'})
        self.split_temp.renderer().setSymbol(layer_transparency)
        self.split_temp.triggerRepaint()
        self.project.addMapLayer(self.split_temp)

    def config_atlas(self):
        """ Load the atlas configuration """
        self.atlas.setEnabled(True)
        self.atlas.setCoverageLayer(self.split_temp)
        self.atlas.setHideCoverage(True)
        self.atlas.setSortFeatures(True)
        self.atlas.setSortExpression("Sort")
        self.atlas.setFilterFeatures(True)

    def export_cartographic_doc(self):
        """
        Cartographic document export's entry point. The function involves the following processes:
            - Set up and load the atlas configuration
            - Export the map atlas and every layout as a image
            - Export the map legend as a image
            - Merge all the images into a single pdf file, and export it to the output directory
        """
        self.set_up_atlas()
        self.export_atlas()
        self.export_legend()
        self.image_to_pdf()

    def export_legend(self):
        """ Export the legend layout as a .jpg file """
        export = QgsLayoutExporter(self.legend)
        settings = QgsLayoutExporter.ImageExportSettings()
        settings.dpi = 150
        export.exportToImage(os.path.join(TEMP_DIR, f'legend-{self.line_id}.tiff'), settings)

    def export_atlas(self):
        """ Export every atlas layout as a .jpg file """
        self.atlas.beginRender()
        self.atlas.first()
        QgsMessageLog.logMessage('Exportant composicions...', level=Qgis.Info)
        settings = QgsLayoutExporter.ImageExportSettings()
        settings.dpi = 150
        for i in range(0, self.atlas.count()):
            # Creata a exporter Layout for each layout generate with Atlas
            exporter = QgsLayoutExporter(self.atlas.layout())
            current_feature_number = str(self.atlas.currentFeatureNumber() + 1)
            atlas_count = str(self.atlas.count())
            QgsMessageLog.logMessage(f'Exportant arxiu: {current_feature_number} de {atlas_count}', level=Qgis.Info)
            exporter.exportToImage(os.path.join(TEMP_DIR, f'{self.atlas.currentFilename()}-{self.line_id}.tiff'),
                                   settings)
            # Create next Layout
            self.atlas.next()

        # Close Atlas Creation
        self.atlas.endRender()
        QgsMessageLog.logMessage('Composicions exportades', level=Qgis.Info)

    def get_pdf_file_name(self):
        """
        Get the pdf file name

        :return: pdf_file_name: Output file name, with format [DCD_<line-id>_<yearmonthday>_<normalized-name-1>_<normalized-name-2>.pdf
        :rtype str
        """
        date = self.date.strftime("%Y%m%d")
        pdf_file_name = f'DCD_{self.line_id}_{date}_{self.muni_1_normalized_name}_{self.muni_2_normalized_name}.pdf'

        return pdf_file_name

    def image_to_pdf(self):
        """
        Get all the generated images and group them as a single pdf file. First, gets the legend image and
        then adds the following map layouts
        """
        QgsMessageLog.logMessage('Fusionant les composicions en un únic arxiu...', level=Qgis.Info)
        # First get a list with the path of the JPG files
        jpg_list = []
        # Append the legend as the first item in the JPG files
        legend_path = os.path.join(TEMP_DIR, f'legend-{self.line_id}.tiff')
        if os.path.exists(legend_path):
            jpg_list.append(legend_path)
        # Append the rest of the JPG files
        for root, dirs, files in os.walk(TEMP_DIR):
            for f in files:
                f_path = os.path.join(root, f)
                if f.endswith('.tiff') and f_path not in jpg_list:
                    jpg_list.append(f_path)

        # Open the first JPG file (legend) as PIL image
        img1 = Image.open(jpg_list[0])
        img1 = img1.convert('RGB')
        # Open the res of JPG files as PIL images and append to a PIL image list
        img_list = []
        for im in jpg_list[1:]:
            img = Image.open(im)
            img = img.convert('RGB')
            img_list.append(img)
        # Merge all the images in a single PDF file
        pdf_file_name = self.get_pdf_file_name()
        img1.save(os.path.join(LAYOUT_OUTPUT, pdf_file_name), save_all=True, append_images=img_list)
        # Close the images to avoid background processes that can lock the files
        img1.close()
        for i in img_list:
            i.close()

    @staticmethod
    def get_symbol(style):
        """
        Return a QGIS symbol from a given style dict

        :param style: Dictionary with the desired style
        :type style: dict

        :return: Symbol with the desired style as a QgsFilSymbol object
        :rtype: QgsFillSymbol
        """
        return QgsFillSymbol.createSimple(style)

    # #######################
    # Validators
    def validate_geometry_layers(self):
        """
        Validate the input layers' geometry

        :return: Indicates if the layers' geometries are valid or not
        :rtype: bool
        """
        # Validate points
        if self.point_del_layer.wkbType() != QgsWkbTypes.PointZ or self.point_rep_layer.wkbType() != QgsWkbTypes.PointZ:
            return False
        # Validate lines
        if self.lin_tram_rep_layer.wkbType() != QgsWkbTypes.MultiLineString or self.lin_tram_ppta_del_layer.wkbType() != QgsWkbTypes.MultiLineString:
            return False

        return True

    # #######################
    # Remove temporal files and reset environment
    def reset_environment(self):
        """ Environment reset's entry point. The function involves the following processes:
            - Remove the coverage layer from the map canvas
            - Remove the temporal files in the temp directory
        """
        self.rm_split_map_layer()
        self.rm_temp()

    def rm_split_map_layer(self):
        """ Remove the splitted layer from the map canvas """
        self.project.removeMapLayer(self.split_temp)

    def rm_temp(self):
        """ Remove the temporal files from the temp directory """
        QgsMessageLog.logMessage('Esborrant arxius temporals...', level=Qgis.Info)
        rm = True
        self.dissolve_temp, self.split_temp = None, None   # In order to avoid process locks and be able to delete the Shapefiles and DBF
        for filename in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, filename)
            try:
                if os.path.exists(file_path) and self.line_id in filename:
                    os.remove(file_path)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error esborrant l'arxiu {filename} => {e}", level=Qgis.Critical)
                rm = False

        if rm:
            QgsMessageLog.logMessage('Arxius temporals esborrats', level=Qgis.Info)
