import subprocess
from sys import stdin, exit
from platformdirs import user_config_dir
from shutil import which
import argparse
import logging


def is_gui_available() -> bool:
    # NOTE: Maybe  replaced with attempt to create window using pyqt
    # and check if it failed.
    return not stdin.isatty()


def config_dir() -> str:
    return user_config_dir(
        "Ghaf",
        ensure_exists=True,
    )


def is_tool_available(name):
    """Check whether `name` is on PATH and marked as executable."""
    # if
    return which(name) is not None


def check_required_tools_availability(required_tools: list[str]) -> None:
    unavailabe_tools = []
    for tool in required_tools:
        if not is_tool_available(tool):
            unavailabe_tools.append(tool)
    if unavailabe_tools != []:
        logging.error(f"Unable to find following tools: {', '.join(unavailabe_tools)}.")
        exit(1)


def parse_args():
    parser = argparse.ArgumentParser(
        prog="Ghaf installation wizard",
        description="Helps you install Ghaf.",
    )
    parser.add_argument(
        "--gui",
        action=argparse.BooleanOptionalAction,
        default=is_gui_available(),
        help="Currently just plug",
    )
    return parser.parse_args()


def run(cmd):
    subprocess.run(cmd, check=True)


def replace_in_file(path, old, new):
    with open(path, "r") as file:
        data = file.read().replace(old, new)

    with open(path, "w") as file:
        file.write(data)
