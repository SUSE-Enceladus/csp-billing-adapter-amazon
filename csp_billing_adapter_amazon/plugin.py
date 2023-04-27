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
import csp_billing_adapter

from datetime import datetime

from csp_billing_adapter.config import Config


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
    client = boto3.client('meteringmarketplace')
    retries = 3

    if len(dimensions) == 1:
        dimension_name = next(iter(dimensions))

        while retries > 0:
            try:
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
                return response.get('MeteringRecordId', None)

        raise exc  # Re-raise exception to calling scope
    else:
        # Placeholder for billing multiple dimensions
        pass


@csp_billing_adapter.hookimpl(trylast=True)
def get_csp_name(config: Config):
    """Return CSP provider name"""
    return 'amazon'


@csp_billing_adapter.hookimpl(trylast=True)
def get_account_info(config: Config):
    """Return a dictionary with account information"""
    pass
