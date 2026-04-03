-- upsert_custom_terms: dict_enabled を DO UPDATE SET に含めない
CREATE OR REPLACE FUNCTION upsert_custom_terms(records JSONB)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE rec JSONB;
BEGIN
    FOR rec IN SELECT * FROM jsonb_array_elements(records) LOOP
        INSERT INTO custom_terms (
            surface_form, reading, pos_type_id, cost,
            source_label, source_url, notes,
            dict_enabled
        ) VALUES (
            rec->>'surface_form',
            rec->>'reading',
            NULLIF(rec->>'pos_type_id', '')::integer,
            COALESCE(NULLIF(rec->>'cost', '')::integer, 5000),
            NULLIF(rec->>'source_label', ''),
            NULLIF(rec->>'source_url', ''),
            NULLIF(rec->>'notes', ''),
            TRUE
        )
        ON CONFLICT (surface_form, reading) DO UPDATE SET
            pos_type_id  = EXCLUDED.pos_type_id,
            cost         = EXCLUDED.cost,
            source_label = EXCLUDED.source_label,
            source_url   = EXCLUDED.source_url,
            notes        = EXCLUDED.notes,
            updated_at   = NOW()
            -- dict_enabled は意図的に除外
        ;
    END LOOP;
END;
$$;
