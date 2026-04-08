from unittest.mock import MagicMock, patch

import pytest

from scripts import manage_dict_enabled


def test_resolve_target_table_for_7_digit_code():
    assert manage_dict_enabled._resolve_target_table("1234567", None) == "ssk_shobyomei"


def test_resolve_target_table_requires_table_for_9_digit_code():
    with pytest.raises(ValueError, match="--table is required"):
        manage_dict_enabled._resolve_target_table("123456789", None)


def test_set_term_enabled_targets_shobyomei_for_7_digits():
    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"shobyomei_code": "1234567"}
    ]

    with patch("scripts.manage_dict_enabled.get_client", return_value=mock_client):
        manage_dict_enabled.set_term_enabled("1234567", table=None, enabled=False)

    mock_client.table.assert_called_once_with("ssk_shobyomei")
    mock_client.table.return_value.update.assert_called_once_with({"dict_enabled": False})
    mock_client.table.return_value.update.return_value.eq.assert_called_once_with(
        "shobyomei_code", "1234567"
    )


def test_set_term_enabled_targets_iyakuhin_for_9_digits():
    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"iyakuhin_code": "123456789"}
    ]

    with patch("scripts.manage_dict_enabled.get_client", return_value=mock_client):
        manage_dict_enabled.set_term_enabled("123456789", table="iyakuhin", enabled=True)

    mock_client.table.assert_called_once_with("ssk_iyakuhin")
    mock_client.table.return_value.update.assert_called_once_with({"dict_enabled": True})
    mock_client.table.return_value.update.return_value.eq.assert_called_once_with(
        "iyakuhin_code", "123456789"
    )
