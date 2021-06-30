@echo off
setlocal ENABLEDELAYEDEXPANSION

rem demanem al user quin id linia vol treballar
set idLinia=%1

rem copiem linia mestra al nou id linia
xcopy /y /i /e /s ".\Linia mestra_v3_ETRS89" ".\%idLinia%"

rem mirem si el replantejament esta en ED50 o ETRS89
set dirName="V:\MapaMunicipal\Linies\%idLinia%\1_Replantejaments\2_SIDM\"
set anterior=0
( dir /b /a "%dirName%" | findstr . ) > nul && (
  set anterior=1
) || (
  set dirName=V:\MapaMunicipal\Linies\%idLinia%\0_ED50\1_Replantejaments\2_SIDM\
  set anterior=2
)

rem check del nom de la carpeta al directori i guardar a variable 
for /f "delims=" %%a in ('dir "%dirName%" /on /ad /b') do @set FOLDER_NAME=%%a

rem copiem carpetes i arxius al work
xcopy /s /i /y "%dirName%%FOLDER_NAME%\DocDelim\Acta" ".\%idLinia%\DocDelim\Acta"
xcopy /s /i /y "%dirName%%FOLDER_NAME%\DocDelim\Cadastre" ".\%idLinia%\DocDelim\Cadastre"
xcopy /s /i /y "%dirName%%FOLDER_NAME%\DocDelim\Fotografies" ".\%idLinia%\DocDelim\Fotografies"
xcopy /s /i /y "%dirName%%FOLDER_NAME%\DocDelim\Planimetries" ".\%idLinia%\DocDelim\Planimetries"
xcopy /s /i /y "%dirName%%FOLDER_NAME%\DocDelim\Proposta" ".\%idLinia%\DocDelim\Proposta"
xcopy /s /i /y "%dirName%%FOLDER_NAME%\DocDelim\Quaderns" ".\%idLinia%\DocDelim\Quaderns"
xcopy /s /i /y "%dirName%%FOLDER_NAME%\DocDelim\Taules" ".\%idLinia%\DocDelim\Taules"

rem NOMES TRANSFORMA SI ESTA EN ED50

if "%anterior%"=="2" (
    rem creació de la carpeta etrs89
    mkdir "C:\Program Files (x86)\ArcPad 7.1\System\SIDM\work\%idLinia%\DocDelim\etrs89"

    rem transformació de les shp a etrs89
    ogr2ogr ".\%idLinia%\DocDelim\etrs89\Lin_tram.shp" "%dirName%%FOLDER_NAME%\DocDelim\Cartografia\Lin_Tram.shp" -s_srs "+proj=utm +zone=31 +ellps=intl +nadgrids=.\100800401.gsb +units=m +no_defs" -t_srs EPSG:25831
    ogr2ogr ".\%idLinia%\DocDelim\etrs89\cerca.shp" "%dirName%%FOLDER_NAME%\DocDelim\Cartografia\cerca.shp" -s_srs "+proj=utm +zone=31 +ellps=intl +nadgrids=.\100800401.gsb +units=m +no_defs" -t_srs EPSG:25831
    ogr2ogr ".\%idLinia%\DocDelim\etrs89\Punt.shp" "%dirName%%FOLDER_NAME%\DocDelim\Cartografia\Punt.shp" -s_srs "+proj=utm +zone=31 +ellps=intl +nadgrids=.\100800401.gsb +units=m +no_defs" -t_srs EPSG:25831
    ogr2ogr ".\%idLinia%\DocDelim\etrs89\Pto_Polig.shp" "%dirName%%FOLDER_NAME%\DocDelim\Cartografia\Pto_Polig.shp" -s_srs "+proj=utm +zone=31 +ellps=intl +nadgrids=.\100800401.gsb +units=m +no_defs" -t_srs EPSG:25831
    ogr2ogr ".\%idLinia%\DocDelim\etrs89\Lin_Polig.shp" "%dirName%%FOLDER_NAME%\DocDelim\Cartografia\Lin_Polig.shp" -s_srs "+proj=utm +zone=31 +ellps=intl +nadgrids=.\100800401.gsb +units=m +no_defs" -t_srs EPSG:25831

    rem copiar shp en etrs89 al work
    xcopy /s /i /y ".\%idLinia%\DocDelim\etrs89\*" ".\%idLinia%\DocDelim\Cartografia"

    xcopy /y ".\%idLinia%\DocDelim\etrs89\Lin_tram.shp" ".\tall5m_shp"
    xcopy /y ".\%idLinia%\DocDelim\etrs89\Lin_tram.apl" ".\tall5m_shp"
    xcopy /y ".\%idLinia%\DocDelim\etrs89\Lin_tram.dbf" ".\tall5m_shp"
    xcopy /y ".\%idLinia%\DocDelim\etrs89\Lin_tram.shx" ".\tall5m_shp"
    xcopy /y ".\%idLinia%\DocDelim\etrs89\Lin_tram.prj" ".\tall5m_shp"
) else (
    xcopy /s /i /y "%dirName%%FOLDER_NAME%\DocDelim\Cartografia\*" ".\%idLinia%\DocDelim\Cartografia"

    xcopy /y ".\%idLinia%\DocDelim\Cartografia\Lin_tram.shp" ".\tall5m_shp"
    xcopy /y ".\%idLinia%\DocDelim\Cartografia\Lin_tram.apl" ".\tall5m_shp"
    xcopy /y ".\%idLinia%\DocDelim\Cartografia\Lin_tram.dbf" ".\tall5m_shp"
    xcopy /y ".\%idLinia%\DocDelim\Cartografia\Lin_tram.shx" ".\tall5m_shp"
    xcopy /y ".\%idLinia%\DocDelim\Cartografia\Lin_tram.prj" ".\tall5m_shp"
)

rem select fulls tall5m
rem chdir a tall5m

chdir ".\tall5m_shp"

rem remove first because it crashes if file exists
del select_tall5m.*

ogr2ogr -f "ESRI Shapefile" -dialect sqlite -sql "SELECT a.* FROM tall5metrs89v10sh0f1r010 a, Lin_tram b WHERE ST_Intersects(a.geometry, b.geometry)" "select_tall5m.shp" .\

rem info from ogrinfo put in a text file to extract tall5m id
ogrinfo -dialect sqlite -sql "SELECT IDABS FROM select_tall5m" select_tall5m.shp > bubu.txt

set last="test"

rem NO tocar la linia buida despres dels sets pq sino peta
for /f "delims=" %%a in ('findstr /b /n /c:"  IDABS (String) = " bubu.txt') do (
  set idFull=%%a
  set idFull=!idFull:~-6!

  if NOT "!idFull!" == "!last!" (
    xcopy /y "\\icgc.local\dades\datacloud_2\bt5m_ETRS89\sid_unzip\!idFull!\*" "..\%idLinia%\CartBase\MT5M" 
    xcopy /y "\\icgc.local\dades\datacloud_2\of5m_ETRS89\jp2_unzip\!idFull!\*" "..\%idLinia%\CartBase\ORTO5M"
    set last=!idFull!

  )
)

del bubu.txt