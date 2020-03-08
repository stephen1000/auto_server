import argparse
import json
import sys

import settings
from lambda_function import controller, lambda_handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("app_name", type=str, help="App service to act upon")
    parser.add_argument(
        "action", type=str, help="Action to perform", choices=controller.actions
    )

    args, body = parser.parse_known_args()
    if body:
        body = " ".join(body)

    action = {"action": args.action, "app_name": args.app_name, "body": body}
    context = {}

    result = lambda_handler(action, context)
    message = result.get("message")
    print(message or "No response")


if __name__ == "__main__":
    main()
