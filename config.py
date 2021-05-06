# +---------------------+
# | VARIABLES I ENTORNS |
# +---------------------+

import os.path as path

# Plugin Local Dir
PLUGIN_LOCAL_DIR = r'C:\Users\fmart\Documents\Work\ICGC\Plugin_UDT'

##############################################################
# GENERADOR MMC

# Llistat de ID Area dels municipis que tenen línia de costa
municipis_costa = ("607", "209", "458", "260", "131", "189", "659", "746", "445", "855", "579", "84", "571", "767",
                   "533", "572", "141", "191", "697", "860", "472", "108", "785", "480", "593", "138", "748", "154",
                   "758", "678", "49", "499", "137", "128", "935", "617", "66", "243", "524", "675", "261", "900",
                   "78", "320", "180", "742", "264", "803", "133", "226", "655", "928", "229", "231", "41", "843",
                   "534", "672", "884", "145", "251", "424", "426", "234", "713", "43", "17", "685", "822", "933")

# Llistat d'arxius temporals
TEMP_ENTITIES = ('MM_Fites.shp', 'MM_Linies.shp', 'MM_Poligons.shp', 'MM_LiniesTaula.dbf', 'MM_LiniaCosta.shp',
                 'MM_LiniaCostaTaula.dbf', 'MM_FullBT5MCosta.dbf')
# Diccionari de Tipus de resolucions al DOGC
DICT_TIPUS_PUB = {'0': 'RESOLUCIO', '1': 'EDICTE', '2': 'CORRECCIO DE DADES', '3': 'ANUNCI', '4': 'DECRET',
                  '5': 'LLEI', '6': 'ORDRE'}

# Generador MMC Paths
GENERADOR_LOCAL_DIR = path.join(PLUGIN_LOCAL_DIR, 'Generador-MMC')
GENERADOR_INPUT_DIR = path.join(GENERADOR_LOCAL_DIR, '01_Entrada')
GENERADOR_WORK_DIR = path.join(GENERADOR_LOCAL_DIR, '02_Treball')
GENERADOR_OUTPUT_DIR = path.join(GENERADOR_LOCAL_DIR, '03_Sortida')
GENERADOR_WORK_GPKG = path.join(GENERADOR_WORK_DIR, 'generador_mmc_database.gpkg')
GENERADOR_TAULES_ESPEC = path.join(GENERADOR_WORK_DIR, 'Taules_espec_C4')
SHAPEFILES_PATH = r'ESRI\Shapefiles'
METADATA_TEMPLATE = path.join(GENERADOR_WORK_DIR, '01_plantillaOriginal.xml')
# Data
DIC_NOM_MUNICIPIS = path.join(GENERADOR_WORK_DIR, 'dic_nom_municipis.csv')
DIC_NOMENS_MUNICIPIS = path.join(GENERADOR_WORK_DIR, 'dic_nomens_municipis.csv')
DIC_LINES = path.join(GENERADOR_WORK_DIR, 'dic_linies_data.csv')
COAST_TXT = path.join(GENERADOR_WORK_DIR, 'treball_fulls5m_costa.txt')
# Paràmetres de les metadades
# Qualsevol canvi als paràmetres de les metadades, s'ha de fer aquí
v_esp_shp = '1.0'
data_esp_shp = '2014-03-24'
nom_institut = 'Institut Cartogràfic i Geològic de Catalunya (ICGC)'
nom_departament = 'Departament de Presidència (DP)'
xml_block = '<gmd:date><gmd:CI_Date><gmd:date><gco:Date>replace_date_here</gco:Date></gmd:date><gmd:dateType><gmd:CI_DateTypeCode codeList="http://idec.icc.cat/schema/Codelist/ML_gmxCodelists.xml" codeListValue="creation" /></gmd:dateType></gmd:CI_Date></gmd:date>'

# ADT POSTGIS CREDENTIALS
HOST = '172.30.29.7'
DBNAME = 'ADT3'
USER = 'adt_ro'
PWD = 'Barcel0n3$'
SCHEMA = 'sidm3'
