#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Webotron: Deploy websites to AWS S3
"""

from pathlib import Path
from mimetypes import guess_type
import boto3
from botocore.exceptions import ClientError
# import sys  # Required to read command, arguments and options, e.g.: webotron.py arg1 arg2 --arg3
import click
from bucket import BucketManager


session = boto3.Session(profile_name='default')  # loads the default section of ~/.aws/config file
bucket_manager = BucketManager(session)


@click.group()  # You can retrieve more information by usint ' webotron.py --help'
def cli():
    """Webotron deploys websites to AWS."""  # Docstring
    pass


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
    s3_bucket = bucket_manager.init_bucket(bucket)
    bucket_policy = bucket_manager.set_policy(s3_bucket)

    policy = """
    {
      "Version":"2012-10-17",
      "Statement":[{
        "Sid":"PublicReadGetObject",
            "Effect":"Allow",
          "Principal": "*",
          "Action":["s3:GetObject"],
          "Resource":["arn:aws:s3:::%s/*"
          ]
        }
      ]
    }
    """ % s3_bucket.name

    # print(policy)

    policy = policy.strip()   # Strip unwanted spaces, tabs and newlines at beginning and end of policy
    pol = s3_bucket.Policy()  # Create an empty policy for the s3_bucket object
    pol.put(Policy=policy)    # Add the policy to the object

    s3_bucket.Website().WebsiteConfiguration = {'ErrorDocument': {'Key': 'error.html'}, 'IndexDocument': {'Suffix': 'index.html'}}

    return


def upload_file(s3_bucket, path, key):
    """Upload path to S3 bucket at key."""
    content_type = guess_type(key)[0] or 'text/plain'
    print('uploading '+str(key))
    s3_bucket.upload_file(
        path,
        key,
        ExtraArgs={
            'ContentType': content_type
        }
    )


@cli.command('sync')
@click.argument('pathname', type=click.Path(exists=True))
@click.argument('bucket')
def sync(pathname, bucket):
    """Sync contents of PATHNAME to BUCKET."""

    s3_bucket = s3.Bucket(bucket)
    root = Path(pathname).expanduser().resolve()  # Resolve to full pathname, convert ~/ to a full user path

    def handle_directory(target):
        for p in target.iterdir():
            if p.is_dir():
                handle_directory(p)
            if p.is_file():
                # print(f"Path: {p}\n Key: {p.relative_to(root)}")
                upload_file(s3_bucket, str(p), str(p.relative_to(root)))

    handle_directory(root)


if __name__ == '__main__':
    # print(sys.argv)
    cli()
