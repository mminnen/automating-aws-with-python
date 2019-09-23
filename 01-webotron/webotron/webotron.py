import boto3
#import sys  # Required to read command, arguments and options, e.g.: webotron.py arg1 arg2 --arg3
import click


session = boto3.Session(profile_name='default')
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


if __name__ == '__main__':
    #print(sys.argv)
    cli()