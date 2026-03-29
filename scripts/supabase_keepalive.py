"""Supabase freeze-prevention script. Runs a minimal SELECT — no writes."""
import logging

from mozc4med_dict.db import get_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

client = get_client()
client.table("import_batches").select("id").limit(1).execute()
logging.info("keep-alive OK: Supabase is reachable")
