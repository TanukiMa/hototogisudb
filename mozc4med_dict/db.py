import os

from dotenv import load_dotenv
from supabase import Client, create_client

# Load .env for local runs. On GHA, env vars are already injected.
load_dotenv()


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)
