DROP TABLE IF EXISTS result_28.kgs_objekte_a;
DROP TABLE IF EXISTS result_28.kgs_count_a_pro_gemeinde;
DROP TABLE IF EXISTS result_28.kgs_a_sub_by_kanton;
DROP TABLE IF EXISTS result_28.kgs_objekt_mit_objektarten;
DROP TABLE IF EXISTS result_28.isos_obperimeter_fk_mit_kgs_count;
DROP TABLE IF EXISTS result_28.kulturerbe_punkte;

-- Aufgabe 1
CREATE TABLE result_28.kgs_objekte_a AS
SELECT
  o.objekt_nr, o.kurztext, o.kanton, o.gemeinde, o.punktkoordinate
FROM kgs_28.kgs_objekt o
JOIN kgs_28.kgs_objekt_kgs_kategorie e
  ON o.kgs_kategorie = e.t_id
WHERE e.ilicode LIKE 'A.%';

-- Aufgabe 2
CREATE TABLE result_28.kgs_count_a_pro_gemeinde AS
SELECT
  o.gemeinde,
  COUNT(*) AS anzahl_kgs_a
FROM kgs_28.kgs_objekt o
JOIN kgs_28.kgs_objekt_kgs_kategorie e
  ON o.kgs_kategorie = e.t_id
WHERE e.ilicode LIKE 'A.%'
GROUP BY o.gemeinde
ORDER BY anzahl_kgs_a DESC;

-- Aufgabe 3
CREATE TABLE result_28.kgs_a_sub_by_kanton AS
SELECT
  o.kanton,
  e.ilicode AS kategorie_sub,
  COUNT(*)  AS anzahl
FROM kgs_28.kgs_objekt o
JOIN kgs_28.kgs_objekt_kgs_kategorie e
  ON o.kgs_kategorie = e.t_id
WHERE e.ilicode LIKE 'A.%'
GROUP BY o.kanton, e.ilicode
ORDER BY o.kanton, e.ilicode;

-- Aufgabe 4
CREATE TABLE result_28.kgs_objekt_mit_objektarten AS
SELECT
  o.objekt_nr,
  o.gemeinde,
  o.kanton,
  o.punktkoordinate,
  STRING_AGG(
    DISTINCT c.objektcode::text,
    ', ' ORDER BY c.objektcode::text
  ) AS objektarten_codes
FROM kgs_28.kgs_objekt AS o
JOIN kgs_28.objektarten_catref AS r
  ON r.kgs_objekt_objektart = o.t_id
JOIN kgs_28.objektarten_catalogue AS c
  ON c.t_id = r.areference
GROUP BY o.objekt_nr, o.gemeinde, o.kanton, o.punktkoordinate;

-- Aufgabe 5
CREATE TABLE result_28.isos_obperimeter_fk_mit_kgs_count AS
WITH gp_norm AS (
  SELECT
    gp.isos_v2isos_ortsbild_geometrie_perimeter AS ob_tid,
    -- SRID normalisieren (du hast 2056, falls 0 → setze 2056)
    CASE
      WHEN ST_SRID(gp.perimeter)=0 THEN ST_SetSRID(gp.perimeter,2056)
      WHEN ST_SRID(gp.perimeter)<>2056 THEN ST_Transform(gp.perimeter,2056)
      ELSE gp.perimeter
    END AS per_2056
  FROM isos_28.geometrie_perimeter gp
  WHERE gp.isos_v2isos_ortsbild_geometrie_perimeter IS NOT NULL
),
ob_poly AS (
  SELECT
    ob_tid,
    ST_UnaryUnion(
      ST_Collect(
        ST_CollectionExtract(
          ST_MakeValid(ST_CurveToLine(per_2056))
        , 3)
      )
    ) AS geom
  FROM gp_norm
  GROUP BY ob_tid
),
kgs_pts AS (
  SELECT
    k.objekt_nr,
    CASE
      WHEN ST_SRID(k.punktkoordinate)=0 THEN ST_SetSRID(k.punktkoordinate,2056)
      WHEN ST_SRID(k.punktkoordinate)<>2056 THEN ST_Transform(k.punktkoordinate,2056)
      ELSE k.punktkoordinate
    END AS geom
  FROM kgs_28.kgs_objekt k
  JOIN kgs_28.kgs_objekt_kgs_kategorie e
    ON e.t_id = k.kgs_kategorie
  WHERE e.ilicode LIKE 'A.%'
    AND k.punktkoordinate IS NOT NULL
)
SELECT
  p.ob_tid,                     -- das ist der "Ortsbild-Schluessel" aus geometrie_perimeter
  COUNT(k.objekt_nr) AS kgs_in_ob
FROM ob_poly p
LEFT JOIN kgs_pts k
  ON ST_Covers(p.geom, k.geom)  -- Rand inklusive (robuster als Within)
GROUP BY p.ob_tid
ORDER BY kgs_in_ob DESC;


-- Aufgabe 6
CREATE TABLE result_28.kulturerbe_punkte AS
/* -------- KGS: Kanton via dispname aus kgs_28.chcantoncode -------- */
WITH kgs_pts AS (
  SELECT
    'KGS_Objekt'::text       AS src,
    o.objekt_nr::text        AS src_id,
    kc.dispname::text        AS kanton,
    o.gemeinde::text         AS gemeinde,
    (
      CASE
        WHEN ST_SRID(o.punktkoordinate)=0     THEN ST_SetSRID(o.punktkoordinate,2056)
        WHEN ST_SRID(o.punktkoordinate)<>2056 THEN ST_Transform(o.punktkoordinate,2056)
        ELSE o.punktkoordinate
      END
    )::geometry(Point,2056)  AS geom
  FROM kgs_28.kgs_objekt o
  LEFT JOIN kgs_28.chcantoncode kc
    ON kc.t_id = o.kanton
  WHERE o.punktkoordinate IS NOT NULL
),

/* -------- ISOS: Kanton pro Ortsbild (Aggregation ueber evtl. mehrere Kantone) -------- */
isos_ob_kanton AS (
  SELECT
    ob.t_id                                        AS ob_tid,
    STRING_AGG(DISTINCT cc.dispname::text, ', ' 
               ORDER BY cc.dispname::text)         AS kanton_disp
  FROM isos_28.ortsbild ob
  JOIN isos_28.kanton k
    ON k.ortsbild_kantone = ob.t_id
  JOIN isos_28.chcantoncode cc
    ON cc.t_id = k.acode   -- deine Beobachtung: acode == chcantoncode.t_id
  GROUP BY ob.t_id
),
/* -------- ISOS: analog fuer die zweite Punktquelle -------- */
isos_ob_v2_kanton AS (
  SELECT
    ob2.t_id                                       AS ob2_tid,
    STRING_AGG(DISTINCT cc.dispname::text, ', ' 
               ORDER BY cc.dispname::text)         AS kanton_disp
  FROM isos_28.isos_v2isos_ortsbild ob2
  JOIN isos_28.kanton k
    ON k.isos_v2isos_ortsbild_kantone = ob2.t_id
  JOIN isos_28.chcantoncode cc
    ON cc.t_id = k.acode
  GROUP BY ob2.t_id
),

/* -------- ISOS: Punkte mit Kanton (dispname) und Gemeinde (aname) -------- */
isos_ob_pts AS (
  SELECT
    'ISOS_Ortsbild'::text      AS src,
    ob.id::text                AS src_id,
    COALESCE(k.kanton_disp,'') AS kanton,          -- falls kein Eintrag, leer
    ob.aname::text             AS gemeinde,        -- wie von dir vorgeschlagen
    (
      CASE
        WHEN ST_SRID(ob.koordinaten)=0     THEN ST_SetSRID(ob.koordinaten,2056)
        WHEN ST_SRID(ob.koordinaten)<>2056 THEN ST_Transform(ob.koordinaten,2056)
        ELSE ob.koordinaten
      END
    )::geometry(Point,2056)    AS geom
  FROM isos_28.ortsbild ob
  LEFT JOIN isos_ob_kanton k
    ON k.ob_tid = ob.t_id
  WHERE ob.koordinaten IS NOT NULL
),

/* -------- ISOS: Punkte mit Kanton (dispname) und Gemeinde (aname) -------- */
isos_ob_v2_pts AS (
  SELECT
    'ISOS_Ortsbild_v2'::text   AS src,
    ob2.id::text               AS src_id,
    COALESCE(k.kanton_disp,'') AS kanton,
    ob2.aname::text            AS gemeinde,
    (
      CASE
        WHEN ST_SRID(ob2.koordinaten)=0     THEN ST_SetSRID(ob2.koordinaten,2056)
        WHEN ST_SRID(ob2.koordinaten)<>2056 THEN ST_Transform(ob2.koordinaten,2056)
        ELSE ob2.koordinaten
      END
    )::geometry(Point,2056)    AS geom
  FROM isos_28.isos_v2isos_ortsbild ob2
  LEFT JOIN isos_ob_v2_kanton k
    ON k.ob2_tid = ob2.t_id
  WHERE ob2.koordinaten IS NOT NULL
),

/* -------- Merge aller drei Quellen -------- */
merged AS (
  SELECT src, src_id, kanton, gemeinde, geom FROM kgs_pts
  UNION ALL
  SELECT src, src_id, kanton, gemeinde, geom FROM isos_ob_pts
  UNION ALL
  SELECT src, src_id, kanton, gemeinde, geom FROM isos_ob_v2_pts
)
SELECT DISTINCT ON (src, src_id)
  src, src_id, NULLIF(kanton,'') AS kanton,  -- leere Strings wieder auf NULL
  gemeinde, geom
FROM merged;

-- sinnvolle Indices
CREATE INDEX IF NOT EXISTS ix_kulturerbe_punkte_v2_geom   ON result_28.kulturerbe_punkte_v2 USING GIST (geom);
CREATE INDEX IF NOT EXISTS ix_kulturerbe_punkte_v2_src_id ON result_28.kulturerbe_punkte_v2 (src, src_id);
