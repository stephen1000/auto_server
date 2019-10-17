"""
The lambda function controlling generation of a server
"""

import os
import time

import boto3
import digitalocean
import paramiko
import requests

from retry import retry

APP_NAME = os.getenv("APP_NAME")
APP_DIR = os.getenv("APP_DIR")
DOCKERFILE = os.getenv("DOCKERFILE")
DIGITALOCEAN_API_TOKEN = os.getenv("DIGITALOCEAN_API_TOKEN")
DIGITALOCEAN_REGION_SLUG = os.getenv("DIGITALOCEAN_REGION_SLUG")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")


class LambdaException(Exception):
    """ Base Exception class for file """


class DropletAlreadyExists(LambdaException):
    """ A droplet for this app already exists """


class DropletDoesNotExist(LambdaException):
    """ No droplet for this app """


class DropletRefusedConnect(LambdaException):
    """ We're having trouble connecting to our server provider for your droplet """


class MultipleDropletsFound(LambdaException):
    """ Too many droplets were returned by this query. """


class AppDroplet(digitalocean.Droplet):
    """ Droplet + convenience methods for when it's bound to an app """

    class NoIpAddress(Exception):
        """ Failed to find an IP address """

    def __init__(self, *args, **kwargs):
        self._ssh_client = None

    @retry(tries=10, delay=3)
    def get_ip_address(self):
        if self.ip_address is None:
            raise self.NoIpAddress("No IP address found")
        return self.ip_address

    @property
    def ssh_client(self):
        """ Returns a SSH client for this droplet """
        if self._ssh_client is None:
            self._ssh_client = self._get_ssh_client()
        return self._ssh_client

    def _get_ssh_client(self):
        client = paramiko.SSHClient()
        # TODO: implement this!
        return client

    def exec(self, command):
        """ Sends a command over SSH to the droplet """
        return self.ssh_client.exec(command)


class Controller(object):
    """
    Controller for a server world 
    """

    ALL_ACTIONS = ["create", "destroy", "hard_destroy", "backup", "restore"]

    def __init__(self, app_name: str = ""):
        self.app_name = app_name
        self._droplet = None
        self.actions = {
            "create": self.create,
            "destroy": self.destroy,
            "hard_destroy": self.hard_destroy,
            "backup": self.backup,
            "restore": self.restore,
        }
        self.manager = digitalocean.Manager(token=DIGITALOCEAN_API_TOKEN)

    def __str__(self):
        return f'App controller for application "{self.app_name}"'

    @property
    def droplet(self):
        """ Provides a lazily loaded droplet for ``self.app_name`` """
        if self._droplet is None:
            self._droplet = self._get_droplet()
        return self._droplet

    def _get_droplet(self):
        """ Calls DigitalOcean's API to fetch a droplet manager """
        droplets = self.manager.get_all_droplets()
        droplets = list(filter(lambda d: d.name == APP_NAME, droplets))

        if len(droplets) > 1:
            raise MultipleDropletsFound
        elif len(droplets) == 0:
            raise DropletDoesNotExist

        droplet = droplets[0]
        return droplet

    def backup(self):
        """ Tarballs app files, and uploads to S3 under ``S3_BUCKET_NAME`` """
        obj_name = f"./{self.app_name}.tar.gz"
        self.droplet.exec(f"tar -zcf {obj_name} /var/bin/{self.app_name}/")
        self.droplet.exec(
            f"aws s3 put-object --bucket {S3_BUCKET_NAME} --key {self.app_name} --body {obj_name}"
        )
        return f'Backed up app "{self.app_name}" to "{S3_BUCKET_NAME}"'

    def restore(self):
        """ Fetches app files from S3 under ``S3_BUCKET_Name`` and extracts """
        # s3 = boto3.client("s3")
        # tarball = s3.get_object(Bucket=S3_BUCKET_NAME, Key=APP_NAME)
        self.droplet.exec(
            f"aws s3 get-object --bucket {S3_BUCKET_NAME} --key {self.app_name}"
        )
        self.droplet.exec(f"tar -xz ./{self.app_name}.tar.gz /var/bin/{self.app_name}")
        return "Restored!"

    def hard_destroy(self):
        return self.destroy(hard=True)

    def destroy(self, hard=False):
        if not hard:
            self.droplet.exec("warn.sh")

        self.backup()
        self.droplet.destroy()

        return "Destroyed!"

    def create(self):
        if self.droplet is not None:
            raise DropletAlreadyExists
        self.droplet.exec(
            "docker run"
            "-it"
            "-p8080:8080"
            "-p25565:25565"
            "-p8123:8123"
            f"--name={self.app_name}"
            f"--mount source={self.app_name}_vol,target={APP_DIR}"
            f"{DOCKERFILE}"
        )
        return f"Created a new dropplet @ {self.droplet.get_ip_address()}"

    def point_route53(self):
        route53 = boto3.client("route53")
        route53.create_traffic_policy_instance(
            HostedZoneID="srv_a_record",
            Name=APP_NAME,
            TTL=3600,
            TrafficPolicyID="srv_a_record",
            TrafficPolicyVersion=1,
        )


controller = Controller()


def lambda_handler(event: dict, context: object):
    """ Actually handles the lambda call """
    action = event["action"]
    app_name = event["app_name"]
    controller.app_name = app_name

    act = controller.actions.get(action)
    if callable(act):
        message = act()
    else:
        message = f"Invalid action: {action}"
    return {"message": message}


if __name__ == "__main__":
    print("To use the cli, call cli.py")
