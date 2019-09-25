#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Webotron: Deploy websites to AWS S3
"""

import boto3
import click
from bucket import BucketManager
# import sys  # Required to read command, arguments and options, e.g.: webotron.py arg1 arg2 --arg3


session = None
bucket_manager = None


@click.group()  # You can retrieve more information by usint ' webotron.py --help'
@click.option('--profile', default='default', help="Use a given AWS profile from ~/.aws/config.")
def cli(profile):
    """Webotron deploys websites to AWS."""  # Docstring

    global session, bucket_manager  # reassign these values, so other functions can use them.
    session_cfg = {}

    if profile:
        session_cfg['profile_name'] = profile
    else:
        session_cfg['profile_name'] = 'default'

    session = boto3.Session(**session_cfg)  # loads the provided section of ~/.aws/config file
    bucket_manager = BucketManager(session)


@cli.command('list-buckets')  # decorator, wraps the function list_buckets() with cli group from click
def list_buckets():
    """List all S3 buckets."""
    for bucket in bucket_manager.all_buckets():
        print(bucket)


@cli.command('list-bucket-objects')  # decorator, wraps the function list_buckets() with cli group from click
@click.argument('bucket')
def list_bucket_objects(bucket):
    """List all objects in an S3 bucket."""
    for obj in bucket_manager.all_objects(bucket):
        print(obj)


@cli.command('setup-bucket')
@click.argument('bucket')
def setup_bucket(bucket):
    """Create and configure S3 bucket."""
    bucket = bucket_manager.init_bucket(bucket)
    bucket_manager.set_policy(bucket)
    bucket_manager.configure_website(bucket)

    return


@cli.command('sync')
@click.argument('pathname', type=click.Path(exists=True))
@click.argument('bucket')
def sync(pathname, bucket):
    """Sync contents of PATHNAME to BUCKET."""

    bucket_manager.sync(pathname, bucket)
    print(bucket_manager.get_bucket_url(bucket_manager.s3.Bucket(bucket)))


if __name__ == '__main__':
    # print(sys.argv)
    cli()
