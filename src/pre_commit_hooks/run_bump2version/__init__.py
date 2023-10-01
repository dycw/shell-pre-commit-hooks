from pathlib import Path
from subprocess import PIPE
from subprocess import STDOUT
from subprocess import CalledProcessError
from subprocess import check_call

from click import command
from click import option
from loguru import logger

from pre_commit_hooks.common import check_versions


@command()
@option(
    "--setup-cfg",
    is_flag=True,
    help="Read `setup.cfg` instead of `bumpversion.cfg`",
)
def main(*, setup_cfg: bool) -> bool:
    """CLI for the `run_bump2version` hook."""
    return _process(setup_cfg=setup_cfg)


def _process(*, setup_cfg: bool) -> bool:
    filename = "setup.cfg" if setup_cfg else ".bumpversion.cfg"
    path = Path(filename)
    pattern = r"current_version = (\d+\.\d+\.\d+)$"
    version = check_versions(path, pattern, name="run-bump2version")
    if version is None:
        return True
    cmd = ["bump2version", "--allow-dirty", f"--new-version={version}", "patch"]
    try:
        _ = check_call(cmd, stdout=PIPE, stderr=STDOUT)  # noqa: S603
    except CalledProcessError as error:
        if error.returncode != 1:
            logger.exception("Failed to run {cmd!r}", cmd=" ".join(cmd))
    except FileNotFoundError:
        logger.exception(
            "Failed to run {cmd!r}. Is `bump2version` installed?",
            cmd=" ".join(cmd),
        )
    else:
        _trim_trailing_whitespaces(path)
        return True
    return False


def _trim_trailing_whitespaces(path: Path, /) -> None:
    with path.open() as fh:
        lines = fh.readlines()
    with path.open(mode="w") as fh:
        fh.writelines([line.rstrip(" ") for line in lines])
