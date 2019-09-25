# -*- coding: utf-8 -*-
"""Classes for S3 buckets."""


from mimetypes import guess_type
from botocore.exceptions import ClientError
from pathlib import Path


class BucketManager:
    """Manage an S3 Bucket."""

    def __init__(self, session):
        """Create a BucketManager object."""
        self.session = session
        self.s3 = self.session.resource('s3')


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


    def set_policy(self, bucket):
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


    def configure_website(self, bucket):
        """Set default web pages."""

        bucket.Website().put(WebsiteConfiguration = {'ErrorDocument': {'Key': 'error.html'},
                                                    'IndexDocument': {'Suffix': 'index.html'}})

    @staticmethod
    def upload_file(bucket, path, key):
        """Upload path to S3 bucket at key."""

        content_type = guess_type(key)[0] or 'text/plain'

        print('uploading ' + str(key))

        return bucket.upload_file(
            path,
            key,
            ExtraArgs={
                'ContentType': content_type
            }
        )


    def sync(self, pathname, bucket_name):
        """Upload all contents in a directory to S3."""

        bucket = self.s3.Bucket(bucket_name)
        root = Path(pathname).expanduser().resolve()  # Resolve to full pathname, convert ~/ to a full user path

        def handle_directory(target):
            for p in target.iterdir():
                if p.is_dir():
                    handle_directory(p)
                if p.is_file():
                    # print(f"Path: {p}\n Key: {p.relative_to(root)}")
                    self.upload_file(bucket, str(p), str(p.relative_to(root)))

        handle_directory(root)

