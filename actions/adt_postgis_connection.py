# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the connection to the ADT PostGIS database is
defined and the data returned.
***************************************************************************/
"""

from qgis.core import QgsVectorLayer, QgsDataSourceUri


class PgADTConnection:
    def __init__(self, host, dbname, user, password, schema):
        self.uri = QgsDataSourceUri()
        self.host = host
        self.dbname = dbname
        self.port = '5342'
        self.schema = schema
        self.user = user
        self.pwd = password

    def connect(self):
        """ Connect to the ADT PostGIS Database """
        self.uri = QgsDataSourceUri()
        self.uri.setConnection(self.host, "5432", self.dbname, self.user, self.pwd)

    def get_table(self, table_name):
        """ Return a table from the ADT PostGIS Database """
        self.uri.setDataSource(self.schema, table_name, None)
        return QgsVectorLayer(self.uri.uri(False), table_name, "postgres")
