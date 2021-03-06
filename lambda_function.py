"""
The lambda function controlling generation of a server
"""

import os
import time

import boto3
import digitalocean
import paramiko
from retry import retry

import settings


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


class MultipleKeysFound(LambdaException):
    """ Too many keys were found for this app """


class NoIpAddress(LambdaException):
    """ Couldn't get an IP address for the droplet """


@retry(tries=30, delay=10)
def connect_ssh_client(client, *args, **kwargs):
    return client.connect(*args, **kwargs)


class Controller(object):
    """
    Controller for a server world 
    """

    ALL_ACTIONS = ["create", "destroy", "hard_destroy", "backup", "restore"]

    def __init__(self, app_name: str = "", message_body: str = ""):
        self.app_name = app_name
        self.message_body = message_body
        self._droplet = None
        self._private_key = None
        self._ssh_key = None
        self._ssh_client = None
        self.actions = {
            "backup": self.backup,
            "configure": self.configure,
            "create": self.create,
            "exec": self.exec,
            "destroy": self.destroy,
            "hard_destroy": self.hard_destroy,
            "restore": self.restore,
        }
        self.manager = digitalocean.Manager(token=settings.DIGITALOCEAN_API_TOKEN)

    def __str__(self):
        return f'App controller for application "{self.app_name}"'

    @retry(NoIpAddress, tries=10, delay=3)
    def get_ip_address(self):
        self.droplet.load()
        if self.droplet.ip_address is None:
            raise NoIpAddress("No IP address found")
        return self.droplet.ip_address

    def _exec(self, command, wait_for_completion: bool = True):
        """ Sends a command over SSH to the droplet """
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        if wait_for_completion:
            stdout.channel.recv_exit_status()
        return stdin, stdout, stderr

    @property
    def ssh_key(self):
        if self._ssh_key is None:
            self._ssh_key = self._create_ssh_key()
        return self._ssh_key

    @retry(tries=10, delay=3)
    def get_ssh_key_fingerprint(self):
        """ Retrieves the fingerprint """
        self.ssh_key.load()
        if self.ssh_key.fingerprint is None:
            raise LambdaException
        return self.ssh_key.fingerprint

    def _get_ssh_key(self):
        """ Retrieves or generates an SSH key """
        keys = list(
            filter(
                lambda x: x.name == settings.APP_NAME, self.manager.get_all_sshkeys()
            )
        )

        if len(keys) > 1:
            raise MultipleKeysFound
        if len(keys) == 0:
            return self._create_ssh_key()

        return keys[0]

    def _create_ssh_key(self):
        """ Creates a new SSH key """
        self._ssh_key = digitalocean.SSHKey(
            token=settings.DIGITALOCEAN_API_TOKEN,
            name=settings.APP_NAME,
            public_key=self.public_key,
        )
        self._ssh_key.create()
        return self._ssh_key

    @property
    def public_key(self):
        """ public portion of key """
        return f"ssh-rsa {self.private_key.get_base64()}"

    @property
    def private_key(self):
        """ Lazy loads pk from s3 or generates a fresh one """
        if self._private_key is None:
            self._private_key = self._get_private_key()
        return self._private_key

    def _get_private_key(self):
        """ Gets or creates a private key """
        try:
            s3_bucket.download_file(
                settings.S3_SSH_KEY_FILE_PATH, settings.SSH_KEY_FILE_NAME,
            )
        except:
            self._create_private_key()

        private_key = paramiko.RSAKey.from_private_key_file(
            settings.SSH_KEY_FILE_NAME, password=settings.PRIVATE_KEY_PASSPHRASE
        )
        return private_key

    def _create_private_key(self):
        """ Generates a new private key and stores it locally and in s3 """
        key = paramiko.RSAKey.generate(2048)
        key.write_private_key_file(
            settings.SSH_KEY_FILE_NAME, password=settings.PRIVATE_KEY_PASSPHRASE
        )
        s3_bucket.upload_file(settings.SSH_KEY_FILE_NAME, settings.S3_SSH_KEY_FILE_PATH)

    @property
    def ssh_client(self):
        """ Returns a SSH client for this droplet """
        if self._ssh_client is None:
            self._ssh_client = self._create_ssh_client()
        return self._ssh_client

    def _create_ssh_client(self) -> paramiko.SSHClient:
        """ Creates an SSH connection to the droplet """
        client = paramiko.SSHClient()
        ip = self.get_ip_address()

        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_ssh_client(
            client, ip, username="root", pkey=self.private_key, timeout=90
        )
        return client

    @property
    def droplet(self):
        """ Provides a lazily loaded droplet for ``self.app_name`` """
        if self._droplet is None:
            self._droplet = self._get_droplet()
            self._configure_droplet()
        return self._droplet

    def _get_droplet(self):
        """ Calls DigitalOcean's API to fetch a droplet manager """
        droplets = self.manager.get_all_droplets()
        droplets = list(filter(lambda d: d.name == settings.APP_NAME, droplets))

        if len(droplets) > 1:
            raise MultipleDropletsFound
        elif len(droplets) == 0:
            return self._create_droplet()

        return droplets[0]

    def _create_droplet(self):
        """ Creates a new droplet """
        self.get_ssh_key_fingerprint()
        self._droplet = digitalocean.Droplet(
            token=settings.DIGITALOCEAN_API_TOKEN,
            name=settings.APP_NAME,
            region=settings.DIGITALOCEAN_REGION_SLUG,
            image="docker-18-04",
            size_slug="4gb",
            ssh_keys=[self.ssh_key.id],
        )
        self._droplet.create()
        return self._droplet

    def _configure_droplet(self):
        """ Run standard configuration on the new droplet """
        self.get_ip_address()
        commands = [
            # create app_dir
            f"mkdir -p {settings.APP_DIR}",
            # ensure we have the packages we need
            f"apt-get --assume-yes update",
            f"apt --assume-yes install awscli",
            # configure AWS
            f"aws configure set AWS_ACCESS_KEY_ID {settings.AWS_ACCESS_KEY_ID}",
            f"aws configure set AWS_SECRET_ACCESS_KEY {settings.AWS_SECRET_ACCESS_KEY}",
            f"aws configure set region {settings.AWS_REGION_ID}",
            f"aws configure set output {settings.AWS_OUTPUT_FORMAT}",
        ]
        for command in commands:
            self._exec(command)
        return "Droplet configured!"

    def configure(self):
        """ Rerun configuration on a droplet """
        return self._configure_droplet()

    def exec(self, command=None):
        """ Run a command on the server. Not to be confused with ``_exec`` """
        if command is None:
            command = self.message_body
        _, stdout, stderr = self._exec(command)
        result = stdout.read().decode() or stderr.read().decode() or "Success"
        return f'Ran command "{command}":\n{result}'

    def backup(self):
        """ Tarballs app files, and uploads to S3 under ``S3_BUCKET_NAME`` """
        self.get_ip_address()
        commands = [
            f"tar -C {settings.APP_DIR} -zcvf {settings.ARCHIVE_FILE_NAME} .",
            f"aws s3 cp {settings.ARCHIVE_FILE_NAME} s3://{settings.S3_BUCKET_NAME}/{settings.S3_ARCHIVE_FILE_PATH}",
        ]
        for command in commands:
            print(self.exec(command))
        return f'Backed up app "{self.app_name}" to "{settings.S3_BUCKET_NAME}"'

    def restore(self):
        """ Fetches app files from S3 under ``S3_BUCKET_Name`` and extracts """
        self.get_ip_address()
        commands = [
            f"aws s3 cp s3://{settings.S3_BUCKET_NAME}/{settings.S3_ARCHIVE_FILE_PATH} {settings.ARCHIVE_FILE_NAME}",
            f"tar -xvzf {settings.ARCHIVE_FILE_NAME} -C {settings.APP_DIR}",
        ]
        for command in commands:
            print(self.exec(command))
        return "Restored!"

    def hard_destroy(self):
        return self.destroy(hard=True)

    def destroy(self, hard=False):
        if not hard:
            self._exec("warn.sh")

        self.backup()
        self.droplet.destroy()

        return "Destroyed!"

    def create(self):
        command = " ".join(
            [
                "docker run",
                "-p 34197:34197/udp",
                "-p 27015:27015/tcp",
                "-it",
                f"--name={self.app_name}",
                "--restart=always",
                f"-v {settings.APP_DIR}:/{self.app_name}",
                f"{settings.DOCKERFILE}",
            ]
        )
        self._exec(command)
        return f"Created a new dropplet @ {self.get_ip_address()}"

    def point_route53(self):
        route53 = boto3.client("route53")
        route53.create_traffic_policy_instance(
            HostedZoneID="srv_a_record",
            Name=settings.APP_NAME,
            TTL=3600,
            TrafficPolicyID="srv_a_record",
            TrafficPolicyVersion=1,
        )


controller = Controller()
s3 = boto3.resource("s3")
s3_bucket = s3.Bucket(settings.S3_BUCKET_NAME)  # pylint: disable=no-member


def lambda_handler(event: dict, context: object):
    """ Actually handles the lambda call """
    action = event["action"]
    app_name = event["app_name"]
    body = event.get("body", "")
    controller.app_name = app_name
    controller.message_body = body

    act = controller.actions.get(action)
    response = act()

    message = f'Called action "{action}" for app "{app_name}".\n'
    if response:
        message += response

    return {"message": message}


if __name__ == "__main__":
    print("To use the cli, call cli.py")
    print("To debug, place a breakpoint here.")
