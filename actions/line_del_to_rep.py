# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the DelimitationToReplantejament class is defined. The main
function of this class is to run the automation process that transforms the
Lin_TramPpta layer into Lin_Tram layer, also updating the GEO_TRAM table.
***************************************************************************/
"""

import os
from osgeo import ogr

from qgis.core import (QgsVectorLayer,
                       QgsField,
                       QgsVectorLayerJoinInfo,
                       QgsFeature,
                       QgsVectorFileWriter,
                       QgsCoordinateTransformContext,
                       QgsProject,
                       QgsCoordinateReferenceSystem)
from qgis.core.additions.edit import edit


class DelimitationToReplantejament:
    """ Delitation to Replantejament transformation class """

    def __init__(self, doc_delim_directory):
        # Paths to directories
        self.doc_delim = doc_delim_directory
        self.carto_dir = os.path.join(doc_delim_directory, 'Cartografia')
        self.tables_dir = os.path.join(doc_delim_directory, 'Taules')
        # Set layers as Vector Layers
        self.lin_tram = QgsVectorLayer(os.path.join(self.carto_dir, 'Lin_Tram.shp'), 'Lin Tram')
        self.lin_tram_ppta = QgsVectorLayer(os.path.join(self.carto_dir, 'Lin_TramPpta.shp'))
        self.geo_tram = QgsVectorLayer(os.path.join(self.tables_dir, 'GEO_TRAM.dbf'), 'Geo tram')
        self.new_lin_tram = QgsVectorLayer('LineString?crs=epsg:25831', 'Lin Tram', 'memory')
        # Input dependant
        self.line_id = self.get_line_id()

    def main(self):
        """
        Main entry point. Transforms the Lin_TramPpta layer into a Lin_Tram layer and updates the GEO_TRAM table
        """
        # Transform Lin_TramPpta to Lin_Tram
        self.transform_del_to_rep()
        # Update the Geo_Tram table
        self.update_geo_tram()

    def transform_del_to_rep(self):
        """
        Transforms the Lin_TramPPta layer into a Lin_Tram layer, getting the old Lin_Tram fields and Lin_TramPpta
        features in order to add those features to a new Lin_Tram memory layer that is going to replace de old one
        """
        new_lin_tram_fields = self.lin_tram.dataProvider().fields()
        provider = self.new_lin_tram.dataProvider()

        with edit(self.new_lin_tram):
            provider.addAttributes(new_lin_tram_fields)
            self.new_lin_tram.updateFields()

        lin_tram_feats = []
        for feat_ppta in self.lin_tram_ppta.getFeatures():
            new_feat = QgsFeature(new_lin_tram_fields)
            new_feat.setGeometry(feat_ppta.geometry())
            # Set attributes
            new_feat['ID'] = 0
            new_feat['ID_SECTOR'] = 1
            new_feat['CORR_DIF'] = 1
            new_feat['ID_TRAM'] = feat_ppta['ID'] / 2
            new_feat['ID_LINIA'] = self.line_id
            new_feat['ID_FITA1'] = feat_ppta['ID_FITA1']
            new_feat['ID_FITA2'] = feat_ppta['ID_FITA2']
            lin_tram_feats.append(new_feat)

        with edit(self.new_lin_tram):
            provider.addFeatures(lin_tram_feats)

        # Delete the old Lin Tram layer
        self.rm_lin_tram_old()
        # Save file
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        QgsVectorFileWriter.writeAsVectorFormat(self.new_lin_tram, os.path.join(self.carto_dir, 'Lin_Tram.shp'),
                                                'utf-8', QgsCoordinateReferenceSystem("EPSG:25831"), 'ESRI Shapefile')

    def rm_lin_tram_old(self):
        """ Remove the old Lin_Tram layer """
        self.lin_tram = None   # In order to avoid process locks and be able to delete the Shapefile
        driver = ogr.GetDriverByName('ESRI Shapefile')
        driver.DeleteDataSource(os.path.join(self.carto_dir, 'Lin_Tram.shp'))

    def update_geo_tram(self):
        """ Update the GEO_TRAM table with Lin_Tram's data """
        geo_tram_provider = self.geo_tram.dataProvider()
        geo_tram_fields = geo_tram_provider.fields()
        self.lin_tram = QgsVectorLayer(os.path.join(self.carto_dir, 'Lin_Tram.shp'), 'Lin Tram')
        tram_id_list = [tram['ID_TRAM'] for tram in self.lin_tram.getFeatures()]

        geo_tram_feats = []
        for tram_id in tram_id_list:
            new_geo_tram = QgsFeature(geo_tram_fields)
            new_geo_tram['ID_LINIA'] = self.line_id
            new_geo_tram['ID_SECTOR'] = 1
            new_geo_tram['ID_TRAM'] = tram_id
            new_geo_tram['GEOMETRIA'] = 22
            new_geo_tram['ID_ORDRE'] = 1
            geo_tram_feats.append(new_geo_tram)

        with edit(self.geo_tram):
            geo_tram_provider.addFeatures(geo_tram_feats)

    # #######################
    # Getters
    def get_line_id(self):
        """
        Get the line ID iterating over the Lin_TramPpta layer
        :return: line_id - ID of the line
        """
        line_id = None
        for tram in self.lin_tram_ppta.getFeatures():
            line_id = tram['ID_LINIA']
            break

        return line_id


