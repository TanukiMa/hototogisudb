import os

import pytest
from supabase import Client, create_client


@pytest.fixture(scope="session")
def client() -> Client:
    url = os.environ["SUPABASE_TEST_URL"]
    key = os.environ["SUPABASE_TEST_SERVICE_ROLE_KEY"]
    return create_client(url, key)


@pytest.fixture(autouse=True)
def use_test_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """db.get_client() がテスト用Supabaseを向くようにenv varを書き換える。"""
    monkeypatch.setenv("SUPABASE_URL", os.environ["SUPABASE_TEST_URL"])
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", os.environ["SUPABASE_TEST_SERVICE_ROLE_KEY"])


@pytest.fixture(autouse=True)
def truncate_tables(client: Client) -> None:
    """Wipe all test data before each test for isolation."""
    for table in [
        "ssk_shobyomei",
        "ssk_iyakuhin",
        "ssk_shinryo_koi",
        "custom_terms",
        "import_batches",
    ]:
        client.table(table).delete().neq("id", 0).execute()
