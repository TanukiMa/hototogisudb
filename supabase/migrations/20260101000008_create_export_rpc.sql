CREATE OR REPLACE FUNCTION export_mozc_dict()
RETURNS TABLE (
    raw_reading  TEXT,
    left_id      INTEGER,
    right_id     INTEGER,
    cost         INTEGER,
    surface_form TEXT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        s.kana_name                            AS raw_reading,
        1849                                   AS left_id,
        1849                                   AS right_id,
        4800                                   AS cost,
        COALESCE(s.base_name, s.abbr_name)     AS surface_form
    FROM ssk_shobyomei s
    WHERE s.dict_enabled = TRUE
      AND COALESCE(s.base_name, s.abbr_name) IS NOT NULL
      AND s.kana_name IS NOT NULL

    UNION ALL

    SELECT
        i.kana_name                            AS raw_reading,
        1849                                   AS left_id,
        1849                                   AS right_id,
        CASE WHEN i.is_generic THEN 5200 ELSE 5000 END AS cost,
        i.kanji_name                           AS surface_form
    FROM ssk_iyakuhin i
    WHERE i.dict_enabled = TRUE
      AND i.kanji_name IS NOT NULL
      AND i.kana_name IS NOT NULL

    UNION ALL

    SELECT
        i.kana_name                            AS raw_reading,
        1849                                   AS left_id,
        1849                                   AS right_id,
        CASE WHEN i.is_generic THEN 5200 ELSE 5000 END AS cost,
        i.generic_name_label                   AS surface_form
    FROM ssk_iyakuhin i
    WHERE i.dict_enabled = TRUE
      AND i.generic_name_label IS NOT NULL
      AND i.kana_name IS NOT NULL

    UNION ALL

    SELECT
        k.abbr_kana_name                               AS raw_reading,
        1849                                           AS left_id,
        1849                                           AS right_id,
        5500                                           AS cost,
        COALESCE(k.abbr_kanji_name, k.base_kanji_name) AS surface_form
    FROM ssk_shinryo_koi k
    WHERE k.dict_enabled = TRUE
      AND COALESCE(k.abbr_kanji_name, k.base_kanji_name) IS NOT NULL
      AND k.abbr_kana_name IS NOT NULL

    UNION ALL

    SELECT
        c.reading                              AS raw_reading,
        COALESCE(p.left_id,  1849)             AS left_id,
        COALESCE(p.right_id, 1849)             AS right_id,
        c.cost                                 AS cost,
        c.surface_form                         AS surface_form
    FROM custom_terms c
    LEFT JOIN pos_types p ON p.id = c.pos_type_id
    WHERE c.dict_enabled = TRUE

    ORDER BY cost, raw_reading
$$;
