-- upsert_ssk_shobyomei: dict_enabled を DO UPDATE SET に含めない
CREATE OR REPLACE FUNCTION upsert_ssk_shobyomei(records JSONB, p_batch_id BIGINT)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE rec JSONB;
BEGIN
    FOR rec IN SELECT * FROM jsonb_array_elements(records) LOOP
        INSERT INTO ssk_shobyomei (
            shobyomei_code, successor_code, base_name, abbr_name, kana_name,
            byomei_mgmt_code, adoption_type, icd10_1, icd10_2,
            change_type, listed_at, changed_at, abolished_at,
            is_active, dict_enabled, batch_id
        ) VALUES (
            rec->>'shobyomei_code',
            rec->>'successor_code',
            rec->>'base_name',
            rec->>'abbr_name',
            rec->>'kana_name',
            rec->>'byomei_mgmt_code',
            rec->>'adoption_type',
            rec->>'icd10_1',
            rec->>'icd10_2',
            rec->>'change_type',
            (rec->>'listed_at')::date,
            (rec->>'changed_at')::date,
            (rec->>'abolished_at')::date,
            (rec->>'is_active')::boolean,
            TRUE,
            p_batch_id
        )
        ON CONFLICT (shobyomei_code) DO UPDATE SET
            successor_code   = EXCLUDED.successor_code,
            base_name        = EXCLUDED.base_name,
            abbr_name        = EXCLUDED.abbr_name,
            kana_name        = EXCLUDED.kana_name,
            byomei_mgmt_code = EXCLUDED.byomei_mgmt_code,
            adoption_type    = EXCLUDED.adoption_type,
            icd10_1          = EXCLUDED.icd10_1,
            icd10_2          = EXCLUDED.icd10_2,
            change_type      = EXCLUDED.change_type,
            listed_at        = EXCLUDED.listed_at,
            changed_at       = EXCLUDED.changed_at,
            abolished_at     = EXCLUDED.abolished_at,
            is_active        = EXCLUDED.is_active,
            batch_id         = EXCLUDED.batch_id,
            imported_at      = NOW()
            -- dict_enabled は意図的に除外
        ;
    END LOOP;
END;
$$;

-- upsert_ssk_iyakuhin: dict_enabled を DO UPDATE SET に含めない
CREATE OR REPLACE FUNCTION upsert_ssk_iyakuhin(records JSONB, p_batch_id BIGINT)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE rec JSONB;
BEGIN
    FOR rec IN SELECT * FROM jsonb_array_elements(records) LOOP
        INSERT INTO ssk_iyakuhin (
            iyakuhin_code, kanji_name, kana_name, base_kanji_name,
            generic_name_code, generic_name_label, is_generic,
            change_type, changed_at, abolished_at,
            is_active, dict_enabled, batch_id
        ) VALUES (
            rec->>'iyakuhin_code',
            rec->>'kanji_name',
            rec->>'kana_name',
            rec->>'base_kanji_name',
            rec->>'generic_name_code',
            rec->>'generic_name_label',
            (rec->>'is_generic')::boolean,
            rec->>'change_type',
            (rec->>'changed_at')::date,
            (rec->>'abolished_at')::date,
            (rec->>'is_active')::boolean,
            TRUE,
            p_batch_id
        )
        ON CONFLICT (iyakuhin_code) DO UPDATE SET
            kanji_name         = EXCLUDED.kanji_name,
            kana_name          = EXCLUDED.kana_name,
            base_kanji_name    = EXCLUDED.base_kanji_name,
            generic_name_code  = EXCLUDED.generic_name_code,
            generic_name_label = EXCLUDED.generic_name_label,
            is_generic         = EXCLUDED.is_generic,
            change_type        = EXCLUDED.change_type,
            changed_at         = EXCLUDED.changed_at,
            abolished_at       = EXCLUDED.abolished_at,
            is_active          = EXCLUDED.is_active,
            batch_id           = EXCLUDED.batch_id,
            imported_at        = NOW()
            -- dict_enabled は意図的に除外
        ;
    END LOOP;
END;
$$;

-- upsert_ssk_shinryo_koi: dict_enabled を DO UPDATE SET に含めない
CREATE OR REPLACE FUNCTION upsert_ssk_shinryo_koi(records JSONB, p_batch_id BIGINT)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE rec JSONB;
BEGIN
    FOR rec IN SELECT * FROM jsonb_array_elements(records) LOOP
        INSERT INTO ssk_shinryo_koi (
            shinryo_koi_code, abbr_kanji_name, abbr_kana_name, base_kanji_name,
            change_type, changed_at, abolished_at,
            is_active, dict_enabled, batch_id
        ) VALUES (
            rec->>'shinryo_koi_code',
            rec->>'abbr_kanji_name',
            rec->>'abbr_kana_name',
            rec->>'base_kanji_name',
            rec->>'change_type',
            (rec->>'changed_at')::date,
            (rec->>'abolished_at')::date,
            (rec->>'is_active')::boolean,
            TRUE,
            p_batch_id
        )
        ON CONFLICT (shinryo_koi_code) DO UPDATE SET
            abbr_kanji_name  = EXCLUDED.abbr_kanji_name,
            abbr_kana_name   = EXCLUDED.abbr_kana_name,
            base_kanji_name  = EXCLUDED.base_kanji_name,
            change_type      = EXCLUDED.change_type,
            changed_at       = EXCLUDED.changed_at,
            abolished_at     = EXCLUDED.abolished_at,
            is_active        = EXCLUDED.is_active,
            batch_id         = EXCLUDED.batch_id,
            imported_at      = NOW()
            -- dict_enabled は意図的に除外
        ;
    END LOOP;
END;
$$;
