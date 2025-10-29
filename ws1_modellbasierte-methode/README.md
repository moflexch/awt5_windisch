## Workshop 1: Modellbasierte Methode mit INTERLIS

Ziel dieses Workshops ist es nicht nur, INTERLIS-Daten in eine Datenbank zu importieren, sondern den gesamten modellbasierten Ansatz kennenzulernen: Wie dienen formale Datenmodelle (z.B. INTERLIS `.ili`) als roter Faden für Import, Validierung, Restrukturierung, Ableitung und Publikation von Geodaten? Du lernst die Prinzipien, typischen Arbeitsschritte und ein Regelwerk zur strukturierten Transformation (Restrukturierung) zwischen Quell- und Zielmodellen kennen. Die Übungen führen dich von den Quellmodellen (ISOS, KGS) zu speziell entworfenen Zielmodellen ("Zielmodelle") für Analyse, Aggregation und vereinheitlichte Publikation.

### Ziele des Workshops
Am Ende kannst du:
1. Erklären, wie der modellbasierte Ansatz mit Restrukturierung funktioniert und worin seine Vorteile liegen. 
2. Ein INTERLIS-Datenmodell lesen und seine Struktur (Themen, Klassen, Attribute, Beziehungen) interpretieren.
3. Rohdaten (XTF/ITF) mittels geeigneter Werkzeuge (ili2pg / Model Baker) in ein relationales Schema importieren.
4. Daten mit dem Modell validieren (iliValidator, integrierte Prüfungen) und Qualitätsfehler erkennen.
5. Ein Regelwerk für die modellbasierte Restrukturierung formulieren (z.B. mittels SQL-Views, Materialized Views, Mapping-Tabellen).
6. Ableitungen und Vereinheitlichungen (normalisieren, klassifizieren, aggregieren) modellkonform erzeugen.
7. Ergebnisse für unterschiedliche Nutzungskontexte (Analyse, Austausch, Publikation) bereitstellen.

### Warum modellbasiert?
Der modellbasierte Ansatz stellt das formale Datenmodell in den Mittelpunkt, anstatt rein dateiformat- oder projektspezifisch zu arbeiten. Vorteile:
- Interoperabilität: Gemeinsame Semantik erlaubt korrektes Zusammenspiel verschiedener Systeme.
- Wiederholbarkeit & Automatisierung: Import-, Validierungs- und Transformationsschritte können skriptbar ausgeführt werden.
- Nachvollziehbarkeit: Regeln sind explizit dokumentiert, nicht als versteckte Einmal-Aktionen.
- Qualitätssicherung: Modellvalidierung (Syntax + Semantik) reduziert Inkonsistenzen.
- Erweiterbarkeit: Neue Anforderungen (z.B. zusätzliche Attribute) lassen sich im Modell beschreiben und systematisch integriert ableiten.

### Was ist Restrukturierung?
Restrukturierung bezeichnet die systematische Abbildung von Daten aus einem Quellmodell (z.B. ISOS, KGS) in eine andere Schemaform (z.B. ein vereinheitlichtes Analyse-Schema oder ein API-orientiertes Publikationsschema). Dabei können:
- Strukturen umgeformt werden (z.B. Auflösung verschachtelter Klassen in flache Tabellen)
- Attribute abgeleitet oder zusammengeführt werden
- Geometrien transformiert werden (z.B. Linien → Flächen, Koordinatensystemwechsel)
- Klassifikationen vereinheitlicht (Mapping von Codes / Domains)
- Aggregationen berechnet (z.B. Anzahl Objekte je Gemeinde)

Typische Regeltypen im Workshop:
- Strukturelle Mappings (FROM Quellklasse TO Zielklasse)
- Attributableitungen (Berechnungen, Concatenation, CASE-Klassifizierung)
- Normalisierung / Denormalisierung (Aufspaltung oder Zusammenführen) 
- Geometrische Transformationen (ST_ Funktionen in PostgreSQL/PostGIS)
- Qualitätsfilter (nur gültige / vollständige Datensätze)

### Kernschritte des modellbasierten Prozesses
1. Modell verstehen: Analyse der `.ili`-Datei (Entitäten, Beziehungen, Domains)
2. Import vorbereiten: Datenquellen + Modelldateien + Kataloge (XML) zusammenstellen
3. Import ausführen: `ili2pg` oder Model Baker generiert Schema + lädt Daten
4. Validierung: Syntax (Parser) + Semantik (Constraints, Domain Checks, OID-Konsistenz) via iliValidator / `ili2pg --validate`
5. Regelwerk anwenden: SQL-Views/Materialized Views, ETL-Skripte oder Model Baker Ableitungsmodelle
6. Ableiten & Restrukturieren: Erstellung neuer Sichten/Schemata für Zielanwendungen
7. Export / Austausch: Rückführung in INTERLIS (falls nötig), oder Bereitstellung über OGC-Dienste / APIs

### Fiktives, minimales Beispiel einer Restrukturierungs-View
```sql
CREATE MATERIALIZED VIEW isos_kgs_objekte_v AS
SELECT 
	o.oid AS objekt_id,
	COALESCE(o.name, o.titel) AS bezeichnung,
	CASE 
		WHEN o.typ IN ('A','B') THEN 'Kategorie_1'
		ELSE 'Kategorie_2'
	END AS kategorie,
	g.gemeindename,
	ST_Area(o.geom) AS flaeche_m2
FROM kgs_objekt o
LEFT JOIN gemeinden g ON ST_Contains(g.geom, o.geom)
WHERE o.status = 'aktiv';
```
Die View bildet Attribute um, klassifiziert Typen, verknüpft Geometrien und berechnet eine Fläche – alles regelbasiert und reproduzierbar.

---

## Voraussetzungen
- Grundkenntnisse in SQL und Datenbanken
- Installierte PostgreSQL-Datenbank (wird vom Workshop-Setup bereitgestellt)
- Java JRE 8 oder höher (z.B. Amazon Corretto oder OpenJDK)
- QGIS 3.22 oder höher plus das Plugin `Model Baker`
- `ili2pg` library zum Importieren von INTERLIS-Daten (entweder standalone oder als Teil von Model Baker)
- INTERLIS-Daten im `.itf`- oder `.xtf`-Format plus, falls nötig, die Katalogdateien (`.xml`) plus das zugehörige INTERLIS-Modell (`.ili`)
- SQL-Client (z.B. pgAdmin, DBeaver)
- Zugangsdaten zur PostgreSQL-Datenbank: Diese findest du unter https://polybox.ethz.ch/index.php/s/i8agPFXCJFTzESy (der Zugang wird nach dem Workshop entfernt). 

## Unterlagen
Die Folien (PDF) liefern eine Einführung in Interoperabilität und die modellbasierte Methode sowie die Übungsserie mit Anleitung. Struktur des Ablageverzeichnisses:
│
├── data/
│   └── ...                      # INTERLIS-Daten (KGS, ISOS + Kataloge)
├── env_files/
│   ├── common.env               # Gemeinsame Umgebungsvariablen
│   └── ...                      # Benutzer-/projektspezifische env-Dateien (Polybox Download)
├── exercise_models/
│   ├── Aufgabe1_KGS_Objekte_A.ili   # Ziel-Modell Übung 1
│   └── ...                          # Weitere Modelle
├── scripts/
│   ├── ILI2DB_IMPORT_COMMANDS_ISOS.txt  # Importbefehle ISOS
│   └── ILI2DB_IMPORT_COMMANDS_KGS.txt   # Importbefehle KGS
├── import_data_to_schema.bat    # Windows-Skript für automatisierten Import
├── INTERLIS_Anwenderinnentreffen_2025_Interoperability.pdf
└── README.md

### Ergänzende Tools / Dateien (optional)
- `QUERIES_KGS_ISOS_DATA.sql`: Beispielhafte Analyse- und Restrukturierungsabfragen
- `KGS_data_import_with_catalogue_data.qgz`: QGIS Projekt zur visuellen Überprüfung
- Log-Dateien (`ilivalidator-*.log`) zur Qualitätsanalyse

### Nächste Schritte im Workshop
1. Modelle sichten (`*.ili`) und zentrale Klassen markieren
2. Import ausführen (Batch oder manuell mit Model Baker)
3. Validierungslog interpretieren
4. Erste Restrukturierungs-View entwerfen
5. Ableitungs-/Mapping-Regeln dokumentieren
6. Ergebnisse evaluieren und verbessern

Viel Erfolg beim Kennenlernen der modellbasierten Methode! 

---

## Zielmodelle der Übungen
Die folgenden sechs INTERLIS-Modelle (im Ordner `scripts/`) definieren die Zieltabellenstrukturen, in welche wir die importierten Quell-Daten transformieren. Sie dienen als Referenz für das Regelwerk (SQL, Views, Materialized Views) sowie für mögliche spätere Exporte zurück nach INTERLIS.

| Aufgabe | Dateiname | Zweck / Inhalt | Bemerkungen |
|---------|-----------|----------------|-------------|
| 1 | `Aufgabe1_KGS_Objekte_A.ili` | Gefilterte KGS-Objekte der Kategorie A als Punkte | Punktkoordinate in EPSG:2056 (LV95) |
| 2 | `Aufgabe2_KGS_Count_A_Pro_Gemeinde.ili` | Aggregation: Anzahl KGS-A pro Gemeinde | Reiner Integer-Wertebereich |
| 3 | `Aufgabe3_KGS_A_Sub_by_Kanton.ili` | Aggregation: Sub-Kategorien (A.*) nach Kanton | Domain für Anzahl definiert |
| 4 | `Aufgabe4_KGS_Objekt_mit_Objektarten.ili` | KGS-Objekte mit aggregierter Liste Objektarten | Liste als Text (kommasepariert) |
| 5 | `Aufgabe5_ISOS_ObPerimeter_FK_mit_KGS_Count.ili` | ISOS-Ortsbild-Perimeter + Anzahl KGS A-Punkte im Polygon | Flächendomain (SURFACE) mit LV95-Koordinaten |
| 6 | `Aufgabe6_Kulturerbe_Punkte.ili` | Vereinheitlichte Punktmenge (KGS + ISOS Varianten) | Vereinheitlichung über `src`-Typ |

Hinweis: Die Geometrie-Domains wurden lokal definiert (Achsenbereiche LV95/EPSG:2056), um externe Modelldependenzen zu vermeiden. Für produktive Nutzung kannst du ein gemeinsames Basis-Geometriemodell einführen oder auf ein offizielles Modell verweisen.

### Transformation in die Zielmodelle
1. Ableitungslogik formulieren (SQL) basierend auf Quelltabellen und Bedingungen der Aufgabe.
2. Datentypen prüfen: Stimmen Textlängen, Zahlenbereiche, Geometrie-Typen mit Zielmodell überein?
3. Aggregationen/Filter anwenden: COUNT, GROUP BY, räumliche Selektionen (z.B. ST_Covers).
4. Qualitätssicherung: Prüfen auf Null-Werte, Duplikate, ungültige Geometrien vor Insert/Export.
5. Optionaler Export: Mit `ili2pg --export` zurück in eine XTF-Datei, die den Zielmodell-Strukturen entspricht.

### Empfehlungen für das Regelwerk
- Verwende gut benannte Views (z.B. `v_kgs_objekte_a`) als Zwischenschritt vor finalen Tabellen.
- Dokumentiere jede Regel (Quelle → Zielattribut) in einem Mapping-Log (Markdown oder Tabelle).
- Setze Constraints in der Datenbank (NOT NULL, CHECK-Bereiche) entsprechend den Modell-Domains.
- Prüfe räumliche Operationen auf SRID-Konformität (immer EPSG:2056 halten).
- Nutze Materialized Views für teure Aggregationen (Aufgaben 2, 3, 5) und reguliere Aktualisierung per Refresh.

### Mögliche Erweiterungen
- Einführung einer Kanton-Domain mit festen Codes (AG, AI, AR, ...)
- Normalisierung der Objektarten (Aufgabe 4) in separate Klassen statt Textliste.
- Gemeinsames Basis-Modell `CommonLV95.ili` (Koordinatendomains, Kantonsliste) zur Vermeidung von Duplikaten.
- METAATTR zur Dokumentation von Herkunft (`@src_table`, `@src_column`).
