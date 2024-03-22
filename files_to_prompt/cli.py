import os
import click
from pathlib import Path
from fnmatch import fnmatch


def should_ignore(path, gitignore_rules):
    for rule in gitignore_rules:
        if fnmatch(os.path.basename(path), rule):
            return True
        if os.path.isdir(path) and fnmatch(os.path.basename(path) + "/", rule):
            return True
    return False


def read_gitignore(path):
    gitignore_path = os.path.join(path, ".gitignore")
    if os.path.isfile(gitignore_path):
        with open(gitignore_path, "r") as f:
            return [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
    return []


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
)
@click.option(
    "--include-hidden",
    is_flag=True,
    help="Include files and folders starting with .",
)
@click.option(
    "--ignore-gitignore",
    is_flag=True,
    help="Ignore .gitignore files and include all files",
)
@click.version_option()
def cli(path, include_hidden, ignore_gitignore):
    """
    Takes a path to a folder and outputs every file in that folder,
    recursively, each one preceded with its filename like this:

    path/to/file.py
    ----
    Contents of file.py goes here

    ---
    path/to/file2.py
    ---
    ...
    """
    gitignore_rules = [] if ignore_gitignore else read_gitignore(path)

    for root, dirs, files in os.walk(path):
        if not include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]

        if not ignore_gitignore:
            gitignore_rules.extend(read_gitignore(root))
            dirs[:] = [
                d
                for d in dirs
                if not should_ignore(os.path.join(root, d), gitignore_rules)
            ]
            files = [
                f
                for f in files
                if not should_ignore(os.path.join(root, f), gitignore_rules)
            ]

        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, "r") as f:
                file_contents = f.read()

            click.echo(file_path)
            click.echo("---")
            click.echo(file_contents)
            click.echo()
            click.echo("---")
