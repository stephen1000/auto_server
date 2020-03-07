import digitalocean
import argparse

import settings

manager = digitalocean.Manager(token=settings.DIGITALOCEAN_API_TOKEN)


def kill_droplets():
    """ Kill all droplets on this account """
    droplets = manager.get_all_droplets()
    for droplet in droplets:
        droplet.destroy()

def kill_keys():
    keys = manager.get_all_sshkeys()
    for key in keys:
        key.destroy()

def kill_all_resources():
    kill_keys()
    kill_droplets()

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", type=str, help="The command to do", choices=["kill"])
    return parser.parse_args()

def main():
    args = get_args()
    if args.command == "kill":
        kill_all_resources()

if __name__ == "__main__":
    kill_all_resources()
