# CSP Billing Adapter Amazon Plugin

This is a plugin for
[csp-billing-adapter](https://github.com/SUSE-Enceladus/csp-billing-adapter)
that provides CSP hook implementations. This includes the hooks defined in the
[csp_hookspecs.py module](https://github.com/SUSE-Enceladus/csp-billing-adapter/blob/main/csp_billing_adapter/csp_hookspecs.py).
To enable metered billing in Amazon the container or instance is required to
have MeterUsage permissions. This can be added with a role policy such as:

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CSPBillingAdapterPermissions",
            "Effect": "Allow",
            "Action": [
                "aws-marketplace:MeterUsage"
            ],
            "Resource": "*"
        }
    ]
}
```

## Meter billing

The `meter_billing` function accepts a dictionary mapping of dimension name
to usage quantity. This information is used to bill the customer for
the product ID that is configured in the adapter. If there is an exception
with metered billing the exception is raised.

## Get CSP Name

The `get_csp_name` function returns the name of the CSP provider. In this
case it is *Amazon*.

## Get Account Info

The `get_account_info` function provides metadata information for the running
instance or container. The structure of this information is as follows:

```
{
    "document": {
        "accountId": "1234567890",
        "architecture": "x86_64",
        "availabilityZone": "us-east-1d",
        "billingProducts": null,
        "devpayProductCodes": null,
        "marketplaceProductCodes": null,
        "imageId": "ami-1234567890abcdefg",
        "instanceId": "i-1234567890abcdefg",
        "instanceType": "t2.micro",
        "kernelId": null,
        "pendingTime": "2023-05-23T19:46:52Z",
        "privateIp": "192.168.0.201",
        "ramdiskId": null,
        "region": "us-east-1",
        "version": "2017-09-30"
    },
    "signature": "signature",
    "pkcs7": "pkcs7",
    "cloud_provider": "amazon"
}
```

This information is pulled from the Amazon Instance metadata endpoint:
http://169.254.169.254/latest. Note: the exact information in the
*document* entry may vary.
