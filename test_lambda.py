"""
Unit tests for the lambda function
"""
import re
from subprocess import check_output

import digitalocean
import pytest

from lambda_function import controller, lambda_handler
from utils import kill_all_resources


def setup_moddule(module):
    """
    Make sure there are no lingering droplets from earlier. Never run this in prod,
    as it kills all droplets in the current environment.
    """
    kill_all_resources()


def test_tests_are_configured():
    assert True


def test_create():
    """ Create a server """
    lambda_handler({"action": "create", "app_name": "factorio"}, object())
    ip = controller.get_ip_address()
    status = check_output(["ping", ip]).decode()
    result_str = re.search(r"Received = (\d)+?,", status)
    if not result_str:
        raise Exception("Unexpected terminal response: " + status)
    received = int(result_str.groups()[0])
    assert received > 0


def teardown_module(module):
    """ 
    Ensure we've killed any droplet we created. Note that this kills all droplets
    on the account it's running in, so make sure you're not doing this in prod!
    """
    kill_all_resources()
