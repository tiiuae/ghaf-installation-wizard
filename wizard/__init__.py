from typing import Any, Callable, Optional
from glob import glob
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.completion import Completer
from prompt_toolkit.completion.word_completer import WordCompleter
from prompt_toolkit.completion.filesystem import PathCompleter
from prompt_toolkit.validation import Validator
from wizard.utils import *
from wizard.validators import *
from dataclasses import dataclass, field
from abc import ABC
from prompt_toolkit import prompt
from os import chdir


# Current context of the wizard step
@dataclass
class Context:
    results: dict[str, Any] = field(default_factory=dict)
    current_step: int = 0

    def next_step(self) -> None:
        self.current_step += 1


@dataclass
class Step(ABC):
    name: str

    def _get_value(self, _: Context) -> Any:
        pass

    def run(self, ctx: Context) -> None:
        value = self._get_value(ctx)
        ctx.results[self.name] = value


@dataclass
class Option(Step):
    prompt: str
    custom_validator: Optional[Validator] = None
    custom_completer: Optional[Completer] = None
    default_value: Optional[Any] = None

    def _get_value(self, _: Context) -> Any:
        return prompt(
            self.prompt,
            validator=self.custom_validator,
            completer=self.custom_completer,
            default=self.default_value or "",
        )


@dataclass
class Variants(Step):
    prompt: str
    variants: list[str]

    def _get_value(self, _: Context) -> Any:
        return prompt(
            self.prompt,
            completer=WordCompleter(self.variants, match_middle=True),
            validator=Validator.from_callable(
                lambda text: text in self.variants,
                error_message=f"This input value is not one of the variants: {' '.join(self.variants)}",
                move_cursor_to_end=True,
            ),
        )


@dataclass
class Wait(Step):
    def __init__(self, prompt: str) -> None:
        self.prompt = prompt

    def run(self, _: Context) -> None:
        print(self.prompt)
        input("Press Enter to continue: ")


@dataclass
class Action(Step):
    def __init__(self, info: str, fn: Callable[[Context], None]) -> None:
        self.info = info
        self.fn = fn

    def run(self, ctx: Context) -> None:
        print(self.info)
        self.fn(ctx)


def generate_template(ctx: Context):
    output_path = ctx.results["output_path"]
    base_system = ctx.results["base_system"]
    ssh_pub = ctx.results["ssh_pub"]
    target_drive_path = ctx.results["target_drive_path"]

    # TODO: Check if there're some files and not do anything in this case
    chdir(output_path)
    run(
        [
            "nix",
            "flake",
            "init",
            "-t" f"github:tiiuae/ghaf#target-x86_64-generic",
        ]
    )

    replace_in_file(
        f"{output_path}/flake.nix", "generic-x86_64-debug", f"{base_system}-debug"
    )
    replace_in_file(f"{output_path}/flake.nix", "SSH_KEY", ssh_pub)
    replace_in_file(f"{output_path}/flake.nix", "DRIVE_PATH", target_drive_path)


# Functions for Action
def build_installer_image(ctx: Context):
    output_path = ctx.results["output_path"]

    run(
        [
            "nix",
            "build",
            "-o" f"{output_path}/result",
            f"{output_path}#nixosConfigurations.PROJ_NAME-ghaf-debug.config.system.build.installer",
        ]
    )


def flash_installer_image(ctx: Context):
    output_path = ctx.results["output_path"]
    installer_image_flush_device = ctx.results["installer_image_flush_device"]

    iso = glob(f"{output_path}/result/iso/nixos-*-linux.iso")[0]

    run(
        [
            "sudo",
            "dd",
            f"if={iso}",
            f"of={installer_image_flush_device}",
            "conv=sync",
            "status=progress",
        ]
    )
    subprocess.run("sync")


def install_config(ctx: Context):
    output_path = ctx.results["output_path"]
    ip_address = ctx.results["ip_address"]

    run(
        [
            "nix",
            "run",
            "github:nix-community/nixos-anywhere",
            "--",
            "--flake",
            f"{output_path}#PROJ_NAME-ghaf-debug",
            f"root@{ip_address}",
        ]
    )


# This class is needed as we need to accumulate suvery results
class Wizard:
    def __init__(self, steps: list[Step], args) -> None:
        self.__args = args

        self.__ctx: Context = Context()

        # NOTE: Map every object to function that just asks user his preference in
        # order to make my life easier when it'll come to adding some gui.
        self.__steps: list[Callable[[Context], None]] = list(
            map(lambda step: step.run, steps)
        )

    def results(self) -> dict[str, Any]:
        return self.__ctx.results

    def evaluate(self) -> None:
        while self.__ctx.current_step in range(0, len(self.__steps)):
            self.__steps[self.__ctx.current_step](self.__ctx)
            self.__ctx.next_step()


def main():
    check_required_tools_availability(
        [
            "nix",
            "sudo",
            "dd",
            "sync",
            "ssh-keygen",
        ]
    )

    print_formatted_text(
        HTML(
            """
<yellow>WARNING:</yellow> Note that command may not work currently
as https://github.com/tiiuae/ghaf/pull/340
for ghaf installer infrastructure not merged yet!
"""
        )
    )

    steps: list[Step] = [
        Option(
            "output_path",
            "Choose config output path: ",
            default_value=config_dir(),
            custom_completer=PathCompleter(),
        ),
        Option(
            "ssh_pub",
            "Your public ssh key: ",
            custom_validator=SshValidator,
        ),
        Variants(
            "base_system",
            "Starting configuration: ",
            ["generic-x86_64", "lenovo-x1-carbon-gen11"],
        ),
        Option(
            "installer_image_flush_device",
            "Path to device on which installer image will be flushed: ",
            default_value="/dev/",
            custom_validator=BlockDeviceValidator,
            custom_completer=PathCompleter(),
        ),
        Option(
            "target_drive_path",
            "Device path on which system will be installed: ",
            default_value="/dev/name_of_the_block_device",
        ),
        Action(
            "Creating flake via Ghaf templates...",
            generate_template,
        ),
        Action("Building installer image...", build_installer_image),
        Action("Flashing installer image...", flash_installer_image),
        Wait(
            """After image were flashed you should run in on the target device,
and connect it to the internet. If you want to connect to wifi, you can use
wifi-connector utility (e.g. `sudo wifi-connector NETWORK PASSWORD`)."""
        ),
        Option(
            "ip_address",
            "Address to which configuration will be deployed: ",
            custom_validator=IpAddressValidator,
        ),
        Action("Installing configuration on the target device...", install_config),
    ]

    wizard = Wizard(steps, parse_args())
    wizard.evaluate()
    print(wizard.results())


if __name__ == "__main__":
    main()
