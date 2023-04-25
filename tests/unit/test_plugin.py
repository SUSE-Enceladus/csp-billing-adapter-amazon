import datetime
import pytest

from unittest.mock import Mock, patch

from csp_billing_adapter_amazon import plugin
from csp_billing_adapter.config import Config
from csp_billing_adapter.adapter import get_plugin_manager

pm = get_plugin_manager()
config = Config.load_from_file(
    'tests/data/good_config.yaml',
    pm.hook
)


def test_setup():
    plugin.setup_adapter(config)  # Currently no-op


@patch('csp_billing_adapter_amazon.plugin.boto3')
def test_meter_billing(mock_boto3):
    client = Mock()
    client.meter_usage.return_value = {'MeteringRecordId': '0123456789'}
    mock_boto3.client.return_value = client

    dimensions = {'tier_1': 10}
    timestamp = datetime.datetime.now(datetime.timezone.utc)

    record_id = plugin.meter_billing(
        config,
        dimensions,
        timestamp,
        dry_run=True
    )

    assert record_id == '0123456789'


@patch('csp_billing_adapter_amazon.plugin.boto3')
def test_meter_billing_error(mock_boto3):
    client = Mock()
    client.meter_usage.side_effect = Exception('Failed to meter bill!')
    mock_boto3.client.return_value = client

    dimensions = {'tier_1': 10}
    timestamp = datetime.datetime.now(datetime.timezone.utc)

    with pytest.raises(Exception):
        plugin.meter_billing(
            config,
            dimensions,
            timestamp,
            dry_run=True
        )


def test_get_csp_name():
    assert plugin.get_csp_name(config) == 'amazon'


def test_get_account_info():
    plugin.get_account_info(config)  # Currently no-op
