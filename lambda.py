"""
The lambda function controlling generation of a server
"""

import os
import time

import boto3
import digitalocean
import paramiko
import requests

APP_NAME = os.getenv("APP_NAME")
DIGITALOCEAN_API_TOKEN = os.getenv("DIGITALOCEAN_API_TOKEN")
DIGITALOCEAN_REGION_SLUG = os.getenv("DIGITALOCEAN_REGION_SLUG")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
SLACK_INCOMING_WEBHOOK_URL = os.getenv("SLACK_INCOMING_WEBHOOK_URL")
MINECRAFT_LAMBDA_FUNCTION_TOKEN = os.getenv("MINECRAFT_LAMBDA_FUNCTION_TOKEN")


def create():
    droplet = make_droplet()
    restore(droplet)


def destroy(hard=False):
    pass


def hard_destroy():
    return destroy(hard=True)


def backup():
    droplet = get_droplet()
    ssh = get_droplet_ssh(droplet)
    obj_name = f"./{APP_NAME}.tar.gz"
    ssh.exec_command(f"tar -zcf {obj_name} /var/bin/{APP_NAME}/")
    ssh.exec_command(
        f"aws s3 put-object --bucket {S3_BUCKET_NAME} --key {APP_NAME} --body {obj_name}"
    )


def restore(droplet=None):
    if not droplet:
        droplet = get_droplet()
    s3 = boto3.client("s3")
    tarball = s3.get_object(APP_NAME)


# Register actions here
actions = {
    "create": create,
    "destroy": destroy,
    "hard_destroy": hard_destroy,
    "backup": backup,
    "restore": restore,
}


def lambda_handler(event, context):
    """ Actually handles the lambda call """
    action = event["text"]
    if action in actions:
        message = actions[action]()
    else:
        message = f"Invalid action: {action}"
    return {"message": message}


def point_route53():
    route53 = boto3.client("route53")
    route53.create_traffic_policy_instance(
        HostedZoneID="srv_a_record",
        Name=APP_NAME,
        TTL=3600,
        TrafficPolicyID="srv_a_record",
        TrafficPolicyVersion=1,
    )


def get_droplet():
    return object()


def make_droplet():
    return object()


def kill_droplet():
    pass


def get_droplet_ssh(droplet):
    return object()
