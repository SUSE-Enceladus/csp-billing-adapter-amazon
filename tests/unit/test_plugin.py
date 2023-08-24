#
# Copyright 2023 SUSE LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import datetime
import pytest
import urllib.error

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


@patch('csp_billing_adapter_amazon.plugin.get_region')
@patch('csp_billing_adapter_amazon.plugin.boto3')
def test_meter_billing(mock_boto3, mock_get_region):
    client = Mock()
    client.meter_usage.return_value = {'MeteringRecordId': '0123456789'}
    mock_boto3.client.return_value = client

    mock_get_region.return_value = 'us-east-1'

    dimensions = {'tier_1': 10}
    timestamp = datetime.datetime.now(datetime.timezone.utc)

    status = plugin.meter_billing(
        config,
        dimensions,
        timestamp,
        dry_run=True
    )

    assert status['tier_1']['record_id'] == '0123456789'
    assert status['tier_1']['status'] == 'submitted'


@patch('csp_billing_adapter_amazon.plugin.get_region')
@patch('csp_billing_adapter_amazon.plugin.boto3')
def test_meter_billing_error(mock_boto3, mock_get_region):
    client = Mock()
    client.meter_usage.side_effect = Exception('Failed to meter bill!')
    mock_boto3.client.return_value = client

    mock_get_region.return_value = 'us-east-1'

    dimensions = {'tier_1': 10}
    timestamp = datetime.datetime.now(datetime.timezone.utc)

    status = plugin.meter_billing(
        config,
        dimensions,
        timestamp,
        dry_run=True
    )

    assert status['tier_1']['error'] == \
        'Failed to meter bill dimension tier_1: Failed to meter bill!'
    assert status['tier_1']['status'] == 'failed'


def test_get_csp_name():
    assert plugin.get_csp_name(config) == 'amazon'


@patch('csp_billing_adapter_amazon.plugin.urllib.request.urlopen')
def test_get_account_info(mock_urlopen):
    urlopen = Mock()
    urlopen.read.side_effect = [
        b'secrettoken',
        b'{"some": "info"}',
        b'signature',
        b'pkcs7'
    ]
    mock_urlopen.return_value = urlopen

    info = plugin.get_account_info(config)
    assert info == {
        'cloud_provider': 'amazon',
        'document': {'some': 'info'},
        'pkcs7': 'pkcs7',
        'signature': 'signature'
    }


@patch('csp_billing_adapter_amazon.plugin._get_ip_addr')
@patch('csp_billing_adapter_amazon.plugin.urllib.request.urlopen')
def test_get_api_header_token_fail(mock_urlopen, mock_get_ip_addr):
    urlopen = Mock()
    urlopen.read.side_effect = [
        urllib.error.URLError('Cannot get token!')
    ]
    mock_urlopen.return_value = urlopen

    with pytest.raises(Exception):
        plugin._get_api_header()


@patch('csp_billing_adapter_amazon.plugin.urllib.request.urlopen')
def test_get_api_header_token_ok(mock_urlopen):
    urlopen = Mock()
    urlopen.read.return_value = b'foo'
    mock_urlopen.return_value = urlopen

    header = plugin._get_api_header()
    assert header == {'X-aws-ec2-metadata-token': 'foo'}


@patch('csp_billing_adapter_amazon.plugin.create_connection')
def test_get_ipv6_addr(mock_create_connection):
    ipv6_addr = plugin._get_ip_addr()
    assert ipv6_addr == '[fd00:ec2::254]'


@patch('csp_billing_adapter_amazon.plugin.has_ipv6', False)
def test_get_ipv4_addr():
    ipv4_addr = plugin._get_ip_addr()
    assert ipv4_addr == '169.254.169.254'


@patch('csp_billing_adapter_amazon.plugin.urllib.request.urlopen')
def test_fetch_metadata_fail(mock_urlopen):
    urlopen = Mock()
    urlopen.read.side_effect = [
        urllib.error.URLError('Cannot get metadata!')
    ]
    mock_urlopen.return_value = urlopen

    metadata = plugin._fetch_metadata('metadata', {'header': 'data'})
    assert metadata is None


@patch('csp_billing_adapter_amazon.plugin._fetch_metadata')
@patch('csp_billing_adapter_amazon.plugin._get_api_header')
def test_get_region(mock_get_header, mock_fetch_metadata):
    mock_get_header.return_value = {'header': 'data'}
    mock_fetch_metadata.return_value = '{"region": "us-east-1"}'

    region = plugin.get_region()
    assert region == 'us-east-1'


@patch('csp_billing_adapter_amazon.plugin._fetch_metadata')
@patch('csp_billing_adapter_amazon.plugin._get_api_header')
def test_get_region_bad_data(mock_get_header, mock_fetch_metadata):
    mock_get_header.return_value = {'header': 'data'}
    mock_fetch_metadata.return_value = '{"other": "data"}'

    with pytest.raises(Exception):
        plugin.get_region()
