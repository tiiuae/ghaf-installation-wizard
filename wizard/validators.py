from ipaddress import ip_address
from subprocess import CalledProcessError, run
from prompt_toolkit.validation import Validator
import json


def is_pub_ssh_key(key: str) -> bool:
    try:
        run(
            ["ssh-keygen", "-l", "-f", "/dev/stdin"],
            check=True,
            input=bytes(key, "utf-8"),
            capture_output=True,
        )
        return True
    except CalledProcessError:
        return False


SshValidator = Validator.from_callable(is_pub_ssh_key, error_message="Invalid ssh key")


def block_devices() -> list[str]:
    process = run(
        ["lsblk", "--json", "-o", "NAME,MOUNTPOINT"],
        capture_output=True,
        text=True,
    )
    blkdevs_info = json.loads(process.stdout)["blockdevices"]

    blkdevs_paths: list[str] = []
    for blkdev_info in blkdevs_info:
        blkdevs_paths.append(f"/dev/{blkdev_info['name']}")

    return blkdevs_paths


def is_available_blk_device(path: str) -> bool:
    return path in block_devices()


BlockDeviceValidator = Validator.from_callable(
    is_available_blk_device, error_message="Invalid block device path"
)


def is_ip_address(s: str) -> bool:
    try:
        ip_address(s)
        return True
    except ValueError:
        return False


IpAddressValidator = Validator.from_callable(
    is_ip_address, error_message="Invalid ip address"
)
