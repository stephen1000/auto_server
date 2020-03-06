import pytest
import digitalocean

import lambda_function

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
    lambda_function.lambda_handler(
        {"action": "create", "app_name": "factorio"}, object()
    )


def teardown_module(module):
    """ 
    Ensure we've killed any droplet we created. Note that this kills all droplets
    on the account it's running in, so make sure you're not doing this in prod!
    """
    kill_all_resources()
