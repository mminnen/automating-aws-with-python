import boto3
from botocore.exceptions import ClientError
#import sys  # Required to read command, arguments and options, e.g.: webotron.py arg1 arg2 --arg3
import click


session = boto3.Session(profile_name='default')  # loads the default section of ~/.aws/config file
s3 = session.resource('s3')


@click.group()  # You can retrieve more information by usint ' webotron.py --help'
def cli():
    "Webotron deploys websites to AWS"  # Docstring
    pass


@cli.command('list-buckets')  # decorator, wraps the function list_buckets() with cli group from click
def list_buckets():
    "List all S3 buckets"
    for bucket in s3.buckets.all():
        print(bucket)


@cli.command('list-bucket-objects')  # decorator, wraps the function list_buckets() with cli group from click
@click.argument('bucket')
def list_bucket_objects(bucket):
    "List all objects in an S3 bucket"
    for obj in s3.Bucket(bucket).objects.all():
        print(obj)


@cli.command('setup-bucket')
@click.argument('bucket')
def setup_bucket(bucket):
    "Create and configure S3 bucket"
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.create_bucket
    s3_bucket = None
    try:
        s3_bucket = s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={'LocationConstraint': session.region_name})
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            s3_bucket = s3.Bucket(bucket)
        else:
            raise e

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

    #print(policy)

    policy = policy.strip()  # Strip unwanted spaces, tabs and newlines at beginning and end of policy
    pol = s3_bucket.Policy() # Create an empty policy for the s3_bucket object
    pol.put(Policy=policy)   # Add the policy to the object

    ws = s3_bucket.Website()
    ws.put(WebsiteConfiguration={'ErrorDocument': {'Key': 'error.html'}, 'IndexDocument': {'Suffix': 'index.html'}})

    return





if __name__ == '__main__':
    #print(sys.argv)
    cli()