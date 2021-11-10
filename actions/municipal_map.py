# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the MunicipalMap class is defined. The main function
of this class is to run the automation process that edits a Municipal map layout,
in order to automatically add some information related to the document and the municipi
and make the layout editable for the user.
***************************************************************************/
"""

import numpy as np
import os
import shutil

from qgis.core import (QgsVectorLayer,
                       QgsProject,
                       QgsMessageLog,
                       QgsRasterLayer,
                       QgsField,
                       QgsMessageLog,
                       Qgis,
                       QgsRectangle)
import processing
from qgis.core.additions.edit import edit

from ..config import *
from ..utils import *
from .adt_postgis_connection import PgADTConnection


class MunicipalMap:
    """ Municipal map generation class """

    def __init__(self, municipi_id, input_directory, iface):
        # ######
        # Initialize instance attributes
        # Set environment variables
        self.municipi_id = municipi_id
        self.input_directory = input_directory
        self.iface = iface
        self.log_environment_variables()
        # ######
        # Common
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        self.rec_table = self.pg_adt.get_table('reconeixement')
        self.dogc_table = self.pg_adt.get_table('pa_pub_dogc')
        self.mtt_table = self.pg_adt.get_table('memoria_treb_top')
        self.project = QgsProject.instance()
        self.arr_municipi_data = np.genfromtxt(LAYOUT_MUNI_DATA, dtype=None, encoding='utf-8-sig', delimiter=';', names=True)
        self.arr_lines_data = np.genfromtxt(LAYOUT_LINE_DATA, dtype=None, encoding='utf-8-sig', delimiter=';', names=True)
        self.layout_manager = self.project.layoutManager()
        # ######
        # Input dependant
        self.municipi_name, self.municipi_nomens = self.get_municipi_name()
        # Paths
        # Reorder the directory
        self.reorder_directory()
        self.set_paths()
        # Layers
        self.set_layers()
        self.act_rec_exists = False
        self.pub_dogc_exits = False
        # Layer dependant
        self.municipi_sup = self.get_municipi_sup()
        self.municipi_lines = self.get_municipi_lines()
        self.mtt_dates = {}
        self.rec_text = self.get_rec_dogc_text()
        self.mtt_text = self.get_mtt_text()

    def log_environment_variables(self):
        """ Log as a MessageLog the environment variables of the DCD """
        QgsMessageLog.logMessage(f'ID Municipi: {self.municipi_id}', level=Qgis.Info)

    # #######################
    # Setters & Getters
    def get_municipi_name(self):
        """
        Get the municipi name depending on the user's municipi ID input
        :return: muni_name - Name of the municipi
        :return: muni_nomens - Nomens of the municipi
        """
        data = np.where(self.arr_municipi_data['id_area'] == f'"{self.municipi_id}"')
        index = data[0][0]
        muni_data = self.arr_municipi_data[index]
        muni_name = muni_data[1]
        muni_nomens = muni_data[5]
        QgsMessageLog.logMessage(f'Nom i nomenclatura de municipi: {muni_name}, {muni_nomens}', level=Qgis.Info)

        return muni_name, muni_nomens

    def get_municipi_sup(self):
        """
        Get the municipi polygon area
        :return: sup - Municipal's polygon area
        """
        sup = None
        for polygon in self.polygon_layer.getFeatures():
            sup = polygon['Sup_CDT']
            QgsMessageLog.logMessage(f'Superfície del municipi: {sup} km quadrats', level=Qgis.Info)
            break

        return sup

    def get_municipi_lines(self):
        """
        Get all the municipal boundary lines that make the input municipi
        :return: line list - List of the municipi's boundary lines
        """
        line_list = []
        for line in self.lines_layer.getFeatures():
            line_id = int(line['id_linia'])
            if not 5000 < line_id < 6000:
                line_list.append(int(line_id))

        QgsMessageLog.logMessage(f"Línies del municipi: {''.join(str(line_list))}", level=Qgis.Info)
        return line_list

    def get_rec_dogc_text(self):
        """
        Get the title of the DOGC publication or acta de reconeixement of every municipi's boundary line, in order
        to write them later in the layout. First of all, the function checks if the line has a DOGC publication
        or acta de reconeixement.
        :return: rec_text_list - List with the title of whether the DOGC titles or Acta de reconeixement titles
                                 of every line
        """
        rec_text_list = []
        for line_id in self.municipi_lines:
            self.rec_table.selectByExpression(f'"id_linia"={line_id} and "vig_act_rec" is True')

            for rec in self.rec_table.getSelectedFeatures():
                text = ''
                rec_date = rec['data_act_rec']
                if isinstance(rec['obs_act_rec'], str):
                    if rec['tipus_doc_ref'] == 2 and 'DOGC' not in rec['obs_act_rec']:
                        self.act_rec_exists = True
                        text = self.get_rec_text(line_id, rec_date)
                    elif rec['tipus_doc_ref'] == 1 or 'DOGC' in rec['obs_act_rec']:
                        self.pub_dogc_exits = True
                        text = self.get_dogc_text(line_id, rec_date)
                else:
                    if rec['tipus_doc_ref'] == 2 and 'DOGC' not in str(rec['obs_act_rec'].value()):
                        self.act_rec_exists = True
                        text = self.get_rec_text(line_id, rec_date)
                    elif rec['tipus_doc_ref'] == 1 or 'DOGC' in str(rec['obs_act_rec'].value()):
                        self.pub_dogc_exits = True
                        text = self.get_dogc_text(line_id, rec_date)
                rec_text_list.append(text)

        QgsMessageLog.logMessage(f"Textos d'actes de reconeixement i publicacions al DOGC: "
                                 f"{''.join(str(rec_text_list))}", level=Qgis.Info)
        return rec_text_list

    def get_rec_text(self, line_id, date):
        """
        Get the title of the acta de reconeixement of the boundary line
        :return: rec_text - Title of the line's Acta de reconeixement
        """
        muni_1_nomens, muni_2_nomens = self.get_municipis_nomens(line_id)
        string_date = self.get_string_date(date)
        rec_text = f'Acta de reconeixement de la línia de terme i assenyalament de les fites comunes dels termes ' \
                   f'municipals {muni_1_nomens} i {muni_2_nomens}, de {string_date}.\n'

        return rec_text

    def get_dogc_text(self, line_id, date):
        """
        Get the title of the DOGC publication of the boundary line
        :return: dogc_text - Title of the line's DOGC publication
        """
        date_ = date.toString("yyyy-MM-dd")
        self.dogc_table.selectByExpression(f'"id_linia"={line_id} AND "vig_pub_dogc" is True AND '
                                           f'"data_doc"=\'{date_}\' AND "tip_pub_dogc" != \'2\'')   # tip_pub_dogc = 2 -> Correcció d'errades, que no poden sortir al document
        dogc_text = ''
        for dogc in self.dogc_table.getSelectedFeatures():
            title = dogc['tit_pub_dogc']
            dogc_text = normalize_dogc_title(title)
            break

        return dogc_text

    def get_mtt_text(self):
        """
        Get the title of the MTT of the boundary line
        :return: mtt_text_list - List of the municipal's boundary lines MTT's titles
        """
        mtt_text_list = []
        for line_id in self.municipi_lines:
            muni_1_nomens, muni_2_nomens = self.get_municipis_nomens(line_id)
            self.mtt_table.selectByExpression(f'"id_linia" = {line_id} AND "vig_mtt" is True')

            for mtt in self.mtt_table.getSelectedFeatures():
                date = mtt['data_doc']
                self.mtt_dates[line_id] = date.toString("yyyyMMdd")   # Add to the MTT dates dict, will be used later
                string_date = self.get_string_date(date)
                mtt_text = f'Memòria dels treballs topogràfics de la línia de delimitació entre els' \
                           f' termes municipals {muni_1_nomens} i {muni_2_nomens}, de {string_date}.\n'
                mtt_text_list.append(mtt_text)
                break

        QgsMessageLog.logMessage(f"Textos de les MTT: {''.join(str(mtt_text_list))}", level=Qgis.Info)
        return mtt_text_list

    def get_municipis_nomens(self, line_id):
        """
        Get the way to name the municipis
        :return: muni_1_nomens - Way to name the first municipi
        :return: muni_2_nomens - Way to name the second municipi
        """
        muni_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)][0]
        muni_1_nomens = muni_data[3]
        muni_2_nomens = muni_data[4]

        return muni_1_nomens, muni_2_nomens

    @staticmethod
    def get_string_date(date):
        """
        Get the current date as a string
        :return: string_date - Current date as string, with format [day month year]
        """
        date = date.toString("yyyy-MM-dd")
        date_splitted = date.split('-')
        day = date_splitted[-1]
        if day[0] == '0':
            day = day[1]
        year = date_splitted[0]
        month = MESOS_CAT[date_splitted[1]]
        string_date = f'{day} {month} {year}'

        return string_date

    @staticmethod
    def get_raster_layer():
        """
        Get the parent raster layer as a QgsRasterLayer
        :return: parent raster layer
        """
        return QgsProject.instance().mapLayersByName('DTM 5m 2020')[0]

    def set_paths(self):
        """ Set the data directories paths """
        self.shapes_dir = os.path.join(self.main_directory, 'ESRI/Shapefiles')

    def set_layers(self):
        """ Set the QGIS Vector Layers """
        try:
            self.lines_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Linies.shp'), 'MM_Linies')
            self.points_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Fites.shp'), 'MM_Fites')
            self.polygon_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Poligons.shp'), 'MM_Poligons')
            self.neighbor_lines_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Lveines.shp'), 'MM_Lveines')
            self.neighbor_polygons_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Municipisveins.shp'), 'MM_Municipisveins')
            self.place_name_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'Nuclis.shp'), 'Nuclis')
            self.map_layers = [self.polygon_layer, self.neighbor_lines_layer, self.lines_layer, self.place_name_layer,
                               self.points_layer, self.neighbor_polygons_layer]
        except Exception as e:
            QgsMessageLog.logMessage(f"Alguna de les capes del Mapa municipal no s'ha pogut definir => {e}", level=Qgis.Critical)

    # #######################
    # Generate the Municipal map layout
    def generate_municipal_map(self):
        """ Entry point for generating the input Municipal's map layout """
        QgsMessageLog.logMessage('Procés iniciat: generació de Mapa municipal', level=Qgis.Info)

        # Set the layout
        QgsMessageLog.logMessage('Preparant composició...', level=Qgis.Info)
        self.remove_map_layers()
        self.add_map_layers()
        self.add_layers_styles()
        self.zoom_to_polygon_layer()
        QgsMessageLog.logMessage('Composició preparada', level=Qgis.Info)
        # Add the labeling field to the points layer
        self.add_labeling_field()
        # Edit the layout
        self.edit_layout()
        # Copy MTT
        self.copy_mtt()

        QgsMessageLog.logMessage('Procés finalitzat: generació de Mapa municipal', level=Qgis.Info)

    def zoom_to_polygon_layer(self):
        """" Zoom the map canvas to the polygon layer """
        # The plugin only zooms correctly if previously exist layers in the map canvas
        self.polygon_layer.selectAll()
        self.iface.mapCanvas().zoomToSelected(self.polygon_layer)
        self.iface.mapCanvas().refresh()
        self.polygon_layer.removeSelection()

    def remove_map_layers(self):
        """ Remove the previous municipal map layers of the canvas """
        layers = self.project.mapLayers().values()
        for layer in layers:
            if layer.name() != 'DTM 5m 2020':
                QgsProject.instance().removeMapLayer(layer)

    def add_map_layers(self):
        """ Add the municipal map layers to the canvas """
        for layer in self.map_layers:
            self.project.addMapLayer(layer)
        # Rearrange the ToC if necessary, depending on if the raster layer exists or not
        raster = self.get_raster_layer()
        if raster:
            self.rearrange_tree_of_contents()

    def rearrange_tree_of_contents(self):
        """ Rearrange the project's tree of contents and add the hillshade raster as the last item """
        raster = self.get_raster_layer()
        root = self.project.layerTreeRoot()
        lyr = root.findLayer(raster.id())
        clone = lyr.clone()
        root.addChildNode(clone)
        parent = lyr.parent()
        parent.removeChildNode(lyr)

    def add_layers_styles(self):
        """ Add style to the newly added layers """
        layers = self.project.mapLayers().values()
        for layer in layers:
            if layer.name() == 'MM_Poligons':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'poligon.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'MM_Fites':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'fites.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'MM_Lveines':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'linies_veines.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'MM_Linies':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'linies.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'MM_Municipisveins':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'etiquetes_municipi_veins.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'Nuclis':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'nuclis.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'Ombra':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'ombra.qml'))
                layer.triggerRepaint()

    def add_labeling_field(self):
        """ Add a labeling field to the points layer, in order to be able to move every point label """
        labeling_field = QgsField('Label', QVariant.Int)
        self.points_layer.dataProvider().addAttributes([labeling_field])
        self.points_layer.updateFields()

        n = 0
        with edit(self.points_layer):
            for feat in self.points_layer.getFeatures():
                n += 1
                feat['Label'] = n
                self.points_layer.updateFeature(feat)

    # ###########
    # Edit layout labels
    def edit_layout(self):
        """ Edit every layout's items with the municipal data """
        QgsMessageLog.logMessage('Editant composició...', level=Qgis.Info)
        layouts_list = self.layout_manager.printLayouts()
        for layout_oj in layouts_list:
            # Get the layout object
            layout = self.layout_manager.layoutByName(layout_oj.name())
            # Edit the layout items
            self.edit_municipi_name_label(layout)
            self.edit_municipi_sup_label(layout)
            self.edit_rec_title_label(layout)
            self.edit_rec_item_label(layout)
            self.edit_mtt_item_label(layout)
        QgsMessageLog.logMessage('Composició editada', level=Qgis.Info)

    def edit_municipi_name_label(self, layout):
        """ Edit the layout's municipal name label """
        municipi_name_item = layout.itemById('Municipi')
        municipi_name_item.setText(self.municipi_name)

    def edit_municipi_sup_label(self, layout):
        """ Edit the layout's municipal area label """
        municipi_name_item = layout.itemById('Sup_CDT')
        municipi_name_item.setText(f'Superfície municipal: {str(self.municipi_sup)} km')

    def edit_rec_title_label(self, layout):
        """
        Edit the Reconeixement title, depending on whether the municipal's boundary lines only have DOGC publication,
        actes de reconeixement or both categories
        """
        text = "Relació d'actes de reconeixement i resolucions publicades al DOGC vigents:"   # Default text
        rec_title_item = layout.itemById('Actes_rec_title')
        if self.act_rec_exists and not self.pub_dogc_exits:
            text = "Relació d'actes de reconeixement vigents:"
        elif self.act_rec_exists and self.pub_dogc_exits:
            text = "Relació d'actes de reconeixement i resolucions publicades al DOGC vigents:"
        elif not self.act_rec_exists and self.pub_dogc_exits:
            text = "Relació de resolucions publicades al DOGC vigents:"

        rec_title_item.setText(text)

    def edit_rec_item_label(self, layout):
        """ Add the titles of both municipal's boundary lines DOGC publications and Actes de reconeixement """
        rec_item = layout.itemById('Actes_rec_items')
        text = ''.join(self.rec_text)
        rec_item.setText(text)

    def edit_mtt_item_label(self, layout):
        """ Add the titles of the municipal's boundary lines MTT """
        mtt_item = layout.itemById('MTT_items')
        text = ''.join(self.mtt_text)
        mtt_item.setText(text)

    # #######################
    # New municipal map directory
    def reorder_directory(self):
        """ Entry point for the new directory generation """
        QgsMessageLog.logMessage('Re-estructurant el directori del MM...', level=Qgis.Info)

        # Create new main directory
        normalized_municipi_name = self.municipi_name.replace("'", "").replace(" ", "-")
        name = f'MM_{normalized_municipi_name}'
        self.main_directory = self.input_directory.replace(self.input_directory.split("\\")[-1], name)
        if not os.path.exists(self.main_directory):
            os.rename(self.input_directory, self.main_directory)
            # Add sub directories
            self.add_sub_directories()
            # Copy files
            self.copy_files()
            # Remove old directories
            self.remove_old_directories()
            # Create txt
            self.create_txt(name)

        QgsMessageLog.logMessage('Directori del MM re-estructurat', level=Qgis.Info)

    def add_sub_directories(self):
        """ Add the pertinent sub directories to the new main directory """
        for dir_ in ('Autocad', 'Memòries_topogràfiques', 'Microstation'):
            os.mkdir(os.path.join(self.main_directory, dir_))
        # Add sub directories to the ESRI directory
        os.mkdir(os.path.join(self.main_directory, 'ESRI', 'layer_propietats'))

    def copy_files(self):
        """ Copy all the necessary files to the new directory """
        dgn_dir = os.path.join(self.main_directory, 'ESRI/DGN')
        # Microstation
        for dgn in os.listdir(dgn_dir):
            if 'Nuclis' not in dgn and 'MM_Lveines' not in dgn and 'MM_Municipisveins' not in dgn:
                shutil.copy(os.path.join(dgn_dir, dgn), os.path.join(self.main_directory, 'Microstation', dgn))
        # AutoCAD
        dxf_dir = os.path.join(self.main_directory, 'ESRI/DXF')
        for cad in os.listdir(dxf_dir):
            if 'Nuclis' not in cad and 'MM_Lveines' not in cad and 'MM_Municipisveins' not in cad:
                shutil.copy(os.path.join(dxf_dir, cad), os.path.join(self.main_directory, 'Autocad', cad))

    def remove_old_directories(self):
        """ Remove the old DXF and DGC directories """
        for directory in os.path.join(self.main_directory, 'ESRI/DGN'), os.path.join(self.main_directory, 'ESRI/DXF'):
            if os.path.exists(directory):
                shutil.rmtree(directory)

    def create_txt(self, name):
        """ Create a info txt file for in new directory """
        with open(os.path.join(self.main_directory, f'{name}.txt'), 'a+') as f:
            f.write('MAPA MUNICIPAL DE CATAlUNYA\n\n')
            f.write(f'Terme municipal {self.municipi_nomens}.\n\n')
            f.write('Sotmès a la consideració de la Comissió de Delimitació Territorial en la seva sessió de <data>.')

    def copy_mtt(self):
        """ Copy the municipal's boundary lines MTT files in the new directory """
        QgsMessageLog.logMessage('Copiant MTT a la carpeta del MM...', level=Qgis.Info)
        for line_id in self.municipi_lines:
            line = str(line_id)
            line_txt = line_id_2_txt(line)   # Line ID in NNNN format
            mtt_date = self.mtt_dates[line_id]
            line_mtt_dir = os.path.join(LINES_DIR, line, MTT_DIR)

            for mtt in os.listdir(line_mtt_dir):
                if mtt.startswith(f'MTT_{line_txt}_{mtt_date}_'):
                    shutil.copy(os.path.join(line_mtt_dir, mtt), os.path.join(self.main_directory,
                                                                              'Memòries_topogràfiques', mtt))

        QgsMessageLog.logMessage('MTT copiades', level=Qgis.Info)


class Hillshade:
    """ Hillshade generation class """

    def __init__(self, input_directory, size):
        # ######
        # Initialize instance attributes
        # Set environment variables
        self.project = QgsProject.instance()
        self.input_directory = input_directory
        self.size = size
        self.layout_name = self.get_layout_name()
        self.xmin, self.ymin, self.xmax, self.ymax = self.get_bounding_box()
        self.log_environment_variables()
        # Input depending variables
        self.output_directory = os.path.join(input_directory, 'ESRI')

    def log_environment_variables(self):
        """ Log as a MessageLog the environment variables of the DCD """
        QgsMessageLog.logMessage(f'Composició: {self.layout_name}', level=Qgis.Info)
        bounding_box = (self.xmin, self.ymin, self.xmax, self.ymax)
        QgsMessageLog.logMessage(f"Caixa de coordenades de l'ombrejat: {bounding_box}", level=Qgis.Info)
        QgsMessageLog.logMessage(f"Carpeta de MM: {self.input_directory}", level=Qgis.Info)

    # #######################
    # Setters & Getters
    def get_layout_name(self):
        """
        Get the layout name depending on the size input given by the user
        :return: Layout name
        """
        return SIZE[self.size]

    def get_bounding_box(self):
        """
        Get the layout bounding box
        :return: Layout's bounding box, a bit larger than it really is
        """
        layout_manager = self.project.layoutManager()
        layout = layout_manager.layoutByName(self.layout_name)
        municipal_map = layout.referenceMap()
        extent = municipal_map.extent()
        # Make the bounding box a bit larger than it really is
        xmin, ymin, xmax, ymax = extent.xMinimum() - 100, extent.yMinimum() - 100, extent.xMaximum() + 100, extent.yMaximum() + 100

        return xmin, ymin, xmax, ymax

    def get_raster_layer(self):
        """
        Get the parent raster layer as a QgsRasterLayer
        :return: parent raster layer
        """
        return self.project.mapLayersByName('DTM 5m 2020')[0]

    def get_clip_layer(self):
        """
        Get the clipped raster layer as a QgsRasterLayer
        :return: clipped raster layer
        """
        return self.project.mapLayersByName('Clipped (extent)')[0]

    def get_hillshade_layer(self):
        """
        Get the hillshade layer as a QgsRasterLayer
        :return: hillshade raster layer
        """
        return self.project.mapLayersByName('ombra')[0]

    # #######################
    # Checkers
    @staticmethod
    def check_dtm_raster():
        """
        Check if the parent raster layer exists in the project tree of contents
        :return: boolean that means whether the parent raster layer exists or not
        """
        raster = QgsProject.instance().mapLayersByName('DTM 5m 2020')
        if len(raster) == 0:
            return False
        else:
            return True

    # #######################
    # Generate the hillshade
    def generate_hillshade(self):
        """ Generate the municipal map hillshade """
        # Clip the DTM raster layer by the Municipal map extent
        self.clip_raster()
        # Generate the hillshade from the clipped raster and add it to the map
        self.hillshade_raster()

    def clip_raster(self):
        """ Clip the parent raster layer with the layout bounding box """
        dtm_raster = self.get_raster_layer()
        parameters = {'INPUT': dtm_raster, 'PROJWIN': QgsRectangle(self.xmin, self.ymin, self.xmax, self.ymax),
                      'OUTPUT': 'TEMPORARY_OUTPUT'}
        processing.runAndLoadResults('gdal:cliprasterbyextent', parameters)

    def hillshade_raster(self):
        """ Generate the hillshade from the translated input raster """
        clip_raster = self.get_clip_layer()
        output = os.path.join(self.output_directory, 'ombra.tif')
        hillshade_parameters = {'INPUT': clip_raster, 'BAND': 1, 'Z_FACTOR': 4,
                                'OUTPUT': output}
        processing.runAndLoadResults('gdal:hillshade', hillshade_parameters)

        # Remove the clipped raster
        self.project.removeMapLayer(clip_raster.id())
        # Append the hillshade raster as the last item, in order to see it as the basemap
        self.rearrange_tree_of_contents()
        # Add style
        self.add_hillshade_style()

    def rearrange_tree_of_contents(self):
        """ Rearrange the project's tree of contents and add the hillshade raster as the last item """
        hillshade = self.get_hillshade_layer()
        root = self.project.layerTreeRoot()
        lyr = root.findLayer(hillshade.id())
        clone = lyr.clone()
        root.addChildNode(clone)
        parent = lyr.parent()
        parent.removeChildNode(lyr)

    def add_hillshade_style(self, ):
        """ Add style to the hillshade layer """
        hillshade = self.get_hillshade_layer()
        hillshade.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'ombra.qml'))
        hillshade.triggerRepaint()
