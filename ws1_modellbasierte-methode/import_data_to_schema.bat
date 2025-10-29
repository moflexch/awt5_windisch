@echo off
setlocal EnableExtensions

REM =====================================================================
REM  Generic GIS Import Script (KGS, ISOS, etc.)
REM  Usage: import_data_to_schema.bat <usernum> <schema_type>
REM  Example: import_data_to_schema.bat 01 kgs
REM =====================================================================

if "%~1"=="" (
  echo Usage: %~nx0 ^<usernummer^> ^<schema_type^>
  echo z.B.:  %~nx0 01 kgs
  exit /b 1
)
if "%~2"=="" (
  echo Usage: %~nx0 ^<usernummer^> ^<schema_type^>
  echo z.B.:  %~nx0 01 kgs
  exit /b 1
)

set "USERNUM=%~1"
set "SCHEMA_TYPE=%~2"

REM Pad USERNUM with leading zero if single digit (1-9 -> 01-09)
if %USERNUM% LSS 10 (
  set "USERNUM=0%USERNUM%"
)

set "USERNAME=iat25_%USERNUM%"
set "ENVFILE=%~dp0env_files\%USERNAME%.env"
set "COMMON=%~dp0env_files\common.env"

if not exist "%ENVFILE%" (
  echo [ERROR] Env-Datei nicht gefunden: "%ENVFILE%"
  exit /b 1
)

REM Load common.env and user env
setlocal EnableDelayedExpansion
if exist "%COMMON%" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%COMMON%") do (
    if not "%%~A"=="" set "%%~A=%%~B"
  )
)
for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%ENVFILE%") do (
  if not "%%~A"=="" set "%%~A=%%~B"
)
REM WICHTIG: KEIN endlocal hier, Variablen behalten!

REM Dynamically set schema variables (convert schema_type to uppercase)
call :UpperCase %SCHEMA_TYPE% SCHEMA_TYPE_UPPER
set "SCHEMA_VAR=%SCHEMA_TYPE_UPPER%_SCHEMA"
set "MODEL_VAR=%SCHEMA_TYPE_UPPER%_MODEL"
set "CATALOG_XML_VAR=%SCHEMA_TYPE_UPPER%_CATALOG_XML"
set "INVENTAR_XTF_VAR=%SCHEMA_TYPE_UPPER%_INVENTAR_XTF"
set "CATALOG_DATASET_VAR=%SCHEMA_TYPE_UPPER%_CATALOG_DATASET"
set "INVENTAR_DATASET_VAR=%SCHEMA_TYPE_UPPER%_INVENTAR_DATASET"

REM Get values from environment
for %%V in (DBUSR DBPWD JAVA ILI2PG_JAR DBHOST DBPORT DBNAME) do (
  if not defined %%V (
    echo [ERROR] %%V fehlt. Bitte in common.env oder %USERNAME%.env setzen.
    exit /b 1
  )
)
for %%V in (!SCHEMA_VAR! !MODEL_VAR! !CATALOG_XML_VAR! !INVENTAR_XTF_VAR! !CATALOG_DATASET_VAR! !INVENTAR_DATASET_VAR!) do (
  if not defined %%V (
    echo [ERROR] %%V fehlt. Bitte in common.env oder %USERNAME%.env setzen.
    exit /b 1
  )
)

REM Assign values to generic names for easier use
set "SCHEMA=!%SCHEMA_VAR%!"
set "MODEL=!%MODEL_VAR%!"
set "CATALOG_XML=!%CATALOG_XML_VAR%!"
set "INVENTAR_XTF=!%INVENTAR_XTF_VAR%!"
set "CATALOG_DATASET=!%CATALOG_DATASET_VAR%!"
set "INVENTAR_DATASET=!%INVENTAR_DATASET_VAR%!"

REM Convert relative paths to absolute paths (relative to script directory)
if not "%CATALOG_XML:~1,1%"==":" (
  set "CATALOG_XML=%~dp0%CATALOG_XML%"
)
if not "%INVENTAR_XTF:~1,1%"==":" (
  set "INVENTAR_XTF=%~dp0%INVENTAR_XTF%"
)

if not exist "%CATALOG_XML%" (
  echo [ERROR] CATALOG_XML existiert nicht: %CATALOG_XML%
  exit /b 1
)
if not exist "%INVENTAR_XTF%" (
  echo [ERROR] INVENTAR_XTF existiert nicht: %INVENTAR_XTF%
  exit /b 1
)

REM Info output

echo [INFO] Benutzer  : %DBUSR%
echo [INFO] Schema    : %SCHEMA%
echo [INFO] Host/Port : %DBHOST%:%DBPORT%  DB: %DBNAME%
echo [INFO] Jar       : %ILI2PG_JAR%
echo [INFO] Model     : %MODEL%
echo [INFO] Catalog   : %CATALOG_XML%
echo [INFO] Inventar  : %INVENTAR_XTF%
echo.

REM Logging
set "LOGDIR=%~dp0logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
for /f "tokens=1-4 delims=/:. " %%a in ("%date% %time%") do set "TS=%%d-%%b-%%c_%%a"
set "LOG1=%LOGDIR%\schemaimport_%USERNAME%_%SCHEMA_TYPE%_%TS%.log"
set "LOG2=%LOGDIR%\import_catalog_%USERNAME%_%SCHEMA_TYPE%_%TS%.log"
set "LOG3=%LOGDIR%\import_inventar_%USERNAME%_%SCHEMA_TYPE%_%TS%.log"

REM 1) Schema anlegen

echo ===================== Schema erstellen =====================
echo "%JAVA%" -jar "%ILI2PG_JAR%" --schemaimport --dbhost %DBHOST% --dbport %DBPORT% --dbusr %DBUSR% --dbpwd ******** --dbdatabase %DBNAME% --dbschema %SCHEMA% --models %MODEL% --defaultSrsAuth EPSG --defaultSrsCode 2056 --coalesceCatalogueRef --createFk --createGeomIdx --createTidCol
echo -------------------------------------------------
echo Wird ausgefuehrt... (siehe %LOG1%)
"%JAVA%" -jar "%ILI2PG_JAR%" --schemaimport --dbhost %DBHOST% --dbport %DBPORT% --dbusr %DBUSR% --dbpwd %DBPWD% --dbdatabase %DBNAME% --dbschema %SCHEMA% ^
  --coalesceCatalogueRef --createNumChecks --createUnique --createFk --createFkIdx ^
  --coalesceMultiSurface --coalesceMultiLine --coalesceMultiPoint --coalesceArray ^
  --beautifyEnumDispName --createGeomIdx --createMetaInfo --expandMultilingual ^
  --createTypeConstraint --createEnumTabsWithId --createTidCol --smart2Inheritance ^
  --strokeArcs --createBasketCol=true --defaultSrsAuth EPSG --defaultSrsCode 2056 ^
  --preScript NULL --postScript NULL --createNlsTab --models %MODEL% --iliMetaAttrs NULL > "%LOG1%" 2>&1

if errorlevel 1 (
  echo [ERROR] Schema-Import fehlgeschlagen. Siehe %LOG1%
  type "%LOG1%"
  exit /b 1
)
echo [OK] Schema-Import erfolgreich
echo.

REM 2) Katalog importieren

echo ===================== Katalogdaten importieren =====================
echo "%JAVA%" -jar "%ILI2PG_JAR%" --import --importTid --dbhost %DBHOST% --dbport %DBPORT% --dbusr %DBUSR% --dbpwd ******** --dbdatabase %DBNAME% --dbschema %SCHEMA% --dataset %CATALOG_DATASET% "%CATALOG_XML%"
echo -------------------------------------------------
echo Wird ausgefuehrt... (siehe %LOG2%)
"%JAVA%" -jar "%ILI2PG_JAR%" --import --importTid --dbhost %DBHOST% --dbport %DBPORT% --dbusr %DBUSR% --dbpwd %DBPWD% --dbdatabase %DBNAME% --dbschema %SCHEMA% ^
  --dataset %CATALOG_DATASET% ^
  --iliMetaAttrs NULL ^
  "%CATALOG_XML%" > "%LOG2%" 2>&1

if errorlevel 1 (
  echo [ERROR] Katalog-Import fehlgeschlagen. Siehe %LOG2%
  type "%LOG2%"
  exit /b 1
)
echo [OK] Katalog-Import erfolgreich
echo.

REM 3) Inventar importieren

echo ===================== Inventardaten importieren =====================
echo "%JAVA%" -jar "%ILI2PG_JAR%" --import --importTid --dbhost %DBHOST% --dbport %DBPORT% --dbusr %DBUSR% --dbpwd ******** --dbdatabase %DBNAME% --dbschema %SCHEMA% --dataset %INVENTAR_DATASET% "%INVENTAR_XTF%"
echo -------------------------------------------------
echo Wird ausgefuehrt... (siehe %LOG3%)
"%JAVA%" -jar "%ILI2PG_JAR%" --import --importTid --dbhost %DBHOST% --dbport %DBPORT% --dbusr %DBUSR% --dbpwd %DBPWD% --dbdatabase %DBNAME% --dbschema %SCHEMA% ^
  --dataset %INVENTAR_DATASET% ^
  --iliMetaAttrs NULL ^
  "%INVENTAR_XTF%" > "%LOG3%" 2>&1

if errorlevel 1 (
  echo [ERROR] Inventar-Import fehlgeschlagen. Siehe %LOG3%
  type "%LOG3%"
  exit /b 1
)
echo [OK] Inventar-Import erfolgreich
echo.

echo [SUCCESS] Import abgeschlossen fuer %DBUSR% (Schema %SCHEMA_TYPE%: %SCHEMA%)
echo Logs:
echo   %LOG1%
echo   %LOG2%
echo   %LOG3%
pause
goto :eof

:UpperCase
REM Convert string to uppercase
REM Usage: call :UpperCase <input> <output_var>
set "_input=%~1"
set "_output="
for %%A in (A B C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
  call set "_input=%%_input:%%A=%%A%%"
)
for %%A in (a b c d e f g h i j k l m n o p q r s t u v w x y z) do (
  call set "_input=%%_input:%%A=%%A%%"
)
set "_input=%_input:a=A%"
set "_input=%_input:b=B%"
set "_input=%_input:c=C%"
set "_input=%_input:d=D%"
set "_input=%_input:e=E%"
set "_input=%_input:f=F%"
set "_input=%_input:g=G%"
set "_input=%_input:h=H%"
set "_input=%_input:i=I%"
set "_input=%_input:j=J%"
set "_input=%_input:k=K%"
set "_input=%_input:l=L%"
set "_input=%_input:m=M%"
set "_input=%_input:n=N%"
set "_input=%_input:o=O%"
set "_input=%_input:p=P%"
set "_input=%_input:q=Q%"
set "_input=%_input:r=R%"
set "_input=%_input:s=S%"
set "_input=%_input:t=T%"
set "_input=%_input:u=U%"
set "_input=%_input:v=V%"
set "_input=%_input:w=W%"
set "_input=%_input:x=X%"
set "_input=%_input:y=Y%"
set "_input=%_input:z=Z%"
set "%~2=%_input%"
goto :eof

endlocal

