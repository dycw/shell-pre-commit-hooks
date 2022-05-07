#!/usr/bin/env python3
from argparse import ArgumentParser
from dataclasses import astuple
from dataclasses import dataclass
from hashlib import md5
from logging import basicConfig
from logging import error
from pathlib import Path
from re import MULTILINE
from re import findall
from subprocess import PIPE  # noqa: S404
from subprocess import STDOUT  # noqa: S404
from subprocess import CalledProcessError  # noqa: S404
from subprocess import check_call  # noqa: S404
from subprocess import check_output  # noqa: S404
from sys import stdout
from typing import Tuple


basicConfig(level="INFO", stream=stdout)


def main() -> int:
    parser = ArgumentParser()
    _ = parser.add_argument("--setup-cfg", action="store_true")
    args = parser.parse_args()
    return int(not _process(setup_cfg=args.setup_cfg))


def _process(*, setup_cfg: bool) -> bool:
    filename = "setup.cfg" if setup_cfg else ".bumpversion.cfg"
    current = _get_current_version(filename)
    master = _get_master_version(filename)
    patched = master.bump_patch()
    if current in {master.bump_major(), master.bump_minor(), patched}:
        return True
    else:
        cmd = [
            "bump2version",
            "--allow-dirty",
            f"--new-version={patched}",
            "patch",
        ]
        try:
            _ = check_call(cmd, stdout=PIPE, stderr=STDOUT)  # noqa: S603
        except CalledProcessError as cperror:
            if cperror.returncode != 1:
                error("Failed to run %r", " ".join(cmd))
        except FileNotFoundError:
            error(
                "Failed to run %r. Is `bump2version` installed?", " ".join(cmd)
            )
        else:
            _trim_trailing_whitespaces(filename)
            return True
        return False


def _get_current_version(filename: str) -> "Version":
    with open(filename) as fh:
        text = fh.read()
    major, minor, patch = _read_versions(text)
    return Version(major, minor, patch)


def _read_versions(text: str) -> Tuple[int, int, int]:
    (group,) = findall(
        r"current_version = (\d+)\.(\d+)\.(\d+)$", text, flags=MULTILINE
    )
    major, minor, patch = map(int, group)
    return major, minor, patch


def _get_master_version(filename: str) -> "Version":
    repo = md5(Path.cwd().as_posix().encode()).hexdigest()  # noqa: S303
    commit = check_output(  # noqa: S603, S607
        ["git", "rev-parse", "origin/master"], text=True
    ).rstrip("\n")
    path = Path.home().joinpath(
        ".cache", "pre-commit-hooks", "run-bump2version", repo, commit
    )
    try:
        with open(path) as fh:
            versions_str = fh.read()
        major, minor, patch = map(int, versions_str.split())
    except FileNotFoundError:
        path.parent.mkdir(parents=True, exist_ok=True)
        contents = check_output(  # noqa: S603, S607
            ["git", "show", f"{commit}:{filename}"], text=True
        )
        major, minor, patch = version_ints = _read_versions(contents)
        versions_str = " ".join(map(str, version_ints))
        with open(path, mode="w") as fh:
            _ = fh.write(versions_str)
    return Version(major, minor, patch)


def _trim_trailing_whitespaces(filename: str) -> None:
    with open(filename) as fh:
        lines = fh.readlines()
    with open(filename, mode="w") as fh:
        fh.writelines([line.rstrip(" ") for line in lines])


@dataclass(repr=False, frozen=True)
class Version:
    major: int
    minor: int
    patch: int

    def __repr__(self) -> str:
        return ".".join(map(str, astuple(self)))

    def __str__(self) -> str:
        return repr(self)

    def bump_major(self) -> "Version":
        return Version(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> "Version":
        return Version(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> "Version":
        return Version(major=self.major, minor=self.minor, patch=self.patch + 1)


if __name__ == "__main__":
    raise SystemExit(main())
