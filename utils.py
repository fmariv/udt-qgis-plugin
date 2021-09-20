# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin
                                 A QGIS plugin

Funcions comuns a tots els móduls.
                              -------------------
        begin                : 2021-04-08
        copyright            : (C) 2021 by ICGC
        author               : Fran Martín
        email                : Francisco.Martin@icgc.cat
***************************************************************************/
"""

from PyQt5.QtCore import QVariant
from qgis.core import QgsField


def line_id_2_txt(line_id):
    """
    Convert line id (integer) to string nnnn
    :return: line_id_txt -> <string> ID de la linia introduit en format text
    """
    line_id_str = str(line_id)
    if len(line_id_str) == 1:
        line_id_txt = "000" + line_id_str
    elif len(line_id_str) == 2:
        line_id_txt = "00" + line_id_str
    elif len(line_id_str) == 3:
        line_id_txt = "0" + line_id_str
    else:
        line_id_txt = line_id_str

    return line_id_txt


def get_common_fields():
    """ Return a list of QGIS fields that are common to many entities """
    id_linia_field = QgsField(name='IdLinia', type=QVariant.String, typeName='text', len=4)
    valid_de_field = QgsField(name='ValidDe', type=QVariant.String, typeName='text', len=8)
    valid_a_field = QgsField(name='ValidA', type=QVariant.String, typeName='text', len=8)
    data_alta_field = QgsField(name='DataAlta', type=QVariant.String, typeName='text', len=12)
    data_baixa_field = QgsField(name='DataBaixa', type=QVariant.String, typeName='text', len=12)

    return id_linia_field, valid_de_field, valid_a_field, data_alta_field, data_baixa_field


def coordinates_to_id_fita(coord_x, coord_y):
    """ Transform point coordinates to it ID, performing a concatenation """
    x = str(round(coord_x, 1))
    y = str(round(coord_y, 1))
    x = x.replace(',', '.')
    y = y.replace(',', '.')
    id_fita = f'{x}_{y}'

    return id_fita


def round_coordinates(coord_x, coord_y):
    """ Round coordinates to 1 decimal """
    x = round(coord_x, 1)
    y = round(coord_y, 1)

    return x, y


def point_num_to_text(num_fita):
    """ Transform point's order number into text """
    num_fita = int(num_fita)
    num_fita_str = str(num_fita)
    if len(num_fita_str) == 1:
        num_fita_txt = "00" + num_fita_str
    elif len(num_fita_str) == 2:
        num_fita_txt = "0" + num_fita_str
    else:
        num_fita_txt = num_fita_str

    return num_fita_txt


def normalize_dogc_title(title):
    """ Normalize a DOGC title in order to capitalize it """
    normalized_title = title.replace("CORRECCIÓ D'ERRADES", "Correcció d'errades").replace("DECRET", "Decret")\
                       .replace("EDICTE", "Edicte").replace("LLEI", "Llei").replace("ORDRE", "Ordre")\
                       .replace("RESOLUCIÓ", "Resolució")
    normalized_title = f'{normalized_title}\n'

    return normalized_title
