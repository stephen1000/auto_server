import argparse
import sys
from lambda_function import lambda_handler, controller

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("app_name", type=str, help="App service to act upon")
    parser.add_argument(
        "action", type=str, help="Action to perform", choices=controller.actions
    )

    args = parser.parse_args()

    action = {"action": args.action, "app_name": args.app_name}
    context = {}

    lambda_handler(action, context)


def get_passed_args():
    if sys.argv[0].lower() == 'python':
        return sys.argv[1:]
    return sys.argv


if __name__ == "__main__":
    main()


