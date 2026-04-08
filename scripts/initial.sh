npx supabase login
npx supabase link
npx supabase db push
python3 scripts/import_shinryo_koi.py --url https://www.ssk.or.jp/seikyushiharai/tensuhyo/kihonmasta/kihonmasta_01.files/s_ALL20260401.zip
python3 scripts/import_shobyomei.py --url https://www.ssk.or.jp/seikyushiharai/tensuhyo/kihonmasta/kihonmasta_07.files/b_20260101.zip
python3 scripts/import_iyakuhin.py --url https://www.ssk.or.jp/seikyushiharai/tensuhyo/kihonmasta/kihonmasta_04.files/y_ALL20260319.zip
python3 scripts/export_mozc_dict.py --dry-run
python3 scripts/export_mozc_dict.py --dry-run --no-skip
python3 scripts/export_mozc_dict.py --no-skip
