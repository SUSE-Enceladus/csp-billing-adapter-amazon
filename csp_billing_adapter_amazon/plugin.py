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

"""
Implements the CSP hook functions for Amazon AWS. This handles the
metered billing of product usage in the AWS Marketplace.
"""

import boto3
import json
import logging
import urllib.request
import urllib.error

import csp_billing_adapter

from datetime import datetime

from csp_billing_adapter.config import Config

log = logging.getLogger('CSPBillingAdapter')

METADATA_ADDR = 'http://169.254.169.254/latest'
METADATA_TOKEN_URL = METADATA_ADDR + '/api/token'


@csp_billing_adapter.hookimpl
def setup_adapter(config: Config):
    """Handle any plugin specific setup at adapter start"""
    pass


@csp_billing_adapter.hookimpl(trylast=True)
def meter_billing(
    config: Config,
    dimensions: dict,
    timestamp: datetime,
    dry_run: bool
):
    """
    Process a metered billing based on the dimensions provided

    If a single dimension is provided the meter_usage API is
    used for the metering. If there is an error the metering
    is attempted 3 times before re-raising the exception to
    calling scope.
    """
    retries = 3

    if len(dimensions) == 1:
        dimension_name = next(iter(dimensions))

        while retries > 0:
            try:
                client = boto3.client(
                    'meteringmarketplace',
                    region_name=get_region()
                )
                response = client.meter_usage(
                    ProductCode=config.product_code,
                    Timestamp=timestamp,
                    UsageDimension=dimension_name,
                    UsageQuantity=dimensions[dimension_name],
                    DryRun=dry_run
                )
            except Exception as error:
                exc = error
                retries -= 1
                continue
            else:
                record_id = response.get('MeteringRecordId', None)
                log.info(f'New metered billing record with ID: {record_id}')
                return record_id

        log.error(f'Failed to meter bill: {str(exc)}')
        raise exc  # Re-raise exception to calling scope
    else:
        # Placeholder for billing multiple dimensions
        pass


@csp_billing_adapter.hookimpl(trylast=True)
def get_csp_name(config: Config):
    """Return CSP provider name"""
    return 'amazon'


def get_region():
    """Return the region name"""
    api_header = _get_api_header()
    document = _fetch_metadata('document', api_header)
    metadata = json.loads(document)
    region = metadata.get('region')

    if not region:
        raise Exception('Unable to retrieve current region.')

    return region


@csp_billing_adapter.hookimpl(trylast=True)
def get_account_info(config: Config):
    """
    Return a dictionary with account information

    The information contains the metadata for document, signature and pkcs7.
    """
    account_info = _get_metadata()
    account_info['document'] = json.loads(account_info.get('document', '{}'))
    account_info['cloud_provider'] = get_csp_name(config)

    return account_info


def _get_api_header():
    """
    Get the header to be used in requests

    Prefer IMDSv2 which requires a token.
    """
    request = urllib.request.Request(
        METADATA_TOKEN_URL,
        headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'},
        method='PUT'
    )

    try:
        token = urllib.request.urlopen(request).read().decode()
    except urllib.error.URLError as error:
        log.error(f'Failed to retrieve metadata token: {str(error)}')
        return {}

    return {'X-aws-ec2-metadata-token': token}


def _get_metadata():
    metadata_options = ['document', 'signature', 'pkcs7']
    metadata = {}
    request_header = _get_api_header()

    for metadata_option in metadata_options:
        metadata[metadata_option] = _fetch_metadata(
            metadata_option,
            request_header
        )

    return metadata


def _fetch_metadata(uri, request_header):
    """Return the response of the metadata request."""
    url = METADATA_ADDR + '/dynamic/instance-identity/' + uri
    data_request = urllib.request.Request(url, headers=request_header)

    try:
        value = urllib.request.urlopen(data_request).read()
    except urllib.error.URLError as error:
        log.error(f'Failed to retrieve metadata for: {url}. {str(error)}')
        return None

    return value.decode()
