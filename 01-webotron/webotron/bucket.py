# -*- coding: utf-8 -*-

"""Classes for S3 buckets."""


from mimetypes import guess_type
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from hashlib import md5
from functools import reduce
from webotron import util  # Imports data and functions to convert AWS region to correct endpoint url.


class BucketManager:
    """Manage an S3 Bucket."""

    # AWS will split large files in chunks of 8388608 bytes, creating a different ETAG for each chunk.
    # https://stackoverflow.com/questions/12186993/what-is-the-algorithm-to-compute-the-amazon-s3-etag-for-a-file-larger-than-5gb
    CHUNK_SIZE = 8388608


    def __init__(self, session):
        """Create a BucketManager object."""
        self.session = session
        self.s3 = self.session.resource('s3')
        self.transfer_config = boto3.s3.transfer.TransferConfig(multipart_chunksize=self.CHUNK_SIZE,
                                                                multipart_threshold=self.CHUNK_SIZE)
        self.manifest = {}


    def get_bucket(self, bucket_name):
        """Get a bucket by name."""
        return self.s3.Bucket(bucket_name)


    def get_region_name(self, bucket):
        """Get the bucket's region name."""
        bucket_location = self.s3.meta.client.get_bucket_location(Bucket=bucket.name)

        return bucket_location["LocationConstraint"] or 'us-east-1'  # The AWS API returns None for us-east-1


    def get_bucket_url(self, bucket):
        """Get the website URL for this bucket."""
        return f"http://{bucket.name}.{util.get_endpoint(self.get_region_name(bucket)).host}"


    def all_buckets(self):
        """Get an iterator for all buckets."""
        return self.s3.buckets.all()


    def all_objects(self, bucket):
        """Get an iterator for all objects in bucket."""
        return self.s3.Bucket(bucket).objects.all()


    def init_bucket(self, bucket_name):
        """Create new bucket, or return existing one by name."""
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.create_bucket
        s3_bucket = None
        try:
            s3_bucket = self.s3.create_bucket(Bucket=bucket_name,
                                         CreateBucketConfiguration={'LocationConstraint': self.session.region_name})
        except ClientError as error:
            if error.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                s3_bucket = self.s3.Bucket(bucket_name)
            else:
                raise error

            return s3_bucket


    @staticmethod
    def set_policy(bucket):
        """Set bucket policy to public readable."""

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
        """ % bucket.name

        # print(policy)

        policy = policy.strip()  # Strip unwanted spaces, tabs and newlines at beginning and end of policy
        pol = bucket.Policy()  # Create an empty policy for the s3_bucket object
        pol.put(Policy=policy)  # Add the policy to the object


    @staticmethod  # Static method knows nothing about the class and just deals with the parameters.
    def configure_website(bucket):
        """Set default web pages."""

        bucket.Website().put(WebsiteConfiguration={'ErrorDocument': {'Key': 'error.html'},
                                                    'IndexDocument': {'Suffix': 'index.html'}})


    def load_manifest(self, bucket):
        """Load manifest for caching purposes."""
        paginator = self.s3.meta.client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket.name):
            for obj in page.get('Contents', []):
                # print(obj)
                self.manifest[obj['Key']] = obj['ETag']


    def upload_file(self, bucket, path, key):
        """Upload path to S3 bucket at key."""

        content_type = guess_type(key)[0] or 'text/plain'

        etag = self.gen_etag(path)
        if self.manifest.get(key, '') == etag:
            print(f"Skipping {key}, (etags match)")
            return

        print('uploading ' + str(key))

        return bucket.upload_file(
            path,
            key,
            ExtraArgs={
                'ContentType': content_type
            },
            Config=self.transfer_config
        )


    @staticmethod
    def hash_data(data):
        """Generate md5 hash for data."""
        hash = md5()
        hash.update(data)

        return hash


    def gen_etag(self, path):
        """Generate ETAG for file."""
        hashes = []

        with open(path, 'rb') as f:
            while True:
                data = f.read(self.CHUNK_SIZE)  # Only read parts of the file in the memory.

                if not data:
                    break

                hashes.append(self.hash_data(data))

        if not hashes:
            return

        elif len(hashes) == 1:
            return f'"{hashes[0].hexdigest()}"'

        else:
            digests = (h.digest() for h in hashes)
            chunk_hash = self.hash_data(reduce(lambda x, y: x + y, digests))  # AWS makes a hash of all the hashes combined
            return f'"{chunk_hash.hexdigest()}-{len(hashes)}"'


    def sync(self, pathname, bucket_name):
        """Upload all contents in a directory to S3."""

        bucket = self.s3.Bucket(bucket_name)
        self.load_manifest(bucket)
        root = Path(pathname).expanduser().resolve()  # Resolve to full pathname, e.g. convert ~/ to a full user path

        def handle_directory(target):
            for p in target.iterdir():
                if p.is_dir():
                    handle_directory(p)
                if p.is_file():
                    # print(f"Path: {p}\n Key: {p.relative_to(root)}")
                    self.upload_file(bucket, str(p), str(p.relative_to(root)))

        handle_directory(root)

