import os
import click
from fnmatch import fnmatch
from . import xml_formatter

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


def process_path(
    path, include_hidden, ignore_gitignore, gitignore_rules, ignore_patterns, output_format
):
    filepaths = []

    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                file_contents = f.read()
            click.echo(path)
            click.echo("---")
            click.echo(file_contents)
            click.echo()
            click.echo("---")
        except UnicodeDecodeError:
            warning_message = f"Warning: Skipping file {path} due to UnicodeDecodeError"
            click.echo(click.style(warning_message, fg="red"), err=True)
    elif os.path.isdir(path):
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

            if ignore_patterns:
                files = [
                    f
                    for f in files
                    if not any(fnmatch(f, pattern) for pattern in ignore_patterns)
                ]

            for file in files:
                if output_format == "claude-xml" or output_format == "claude-xml-b64":
                    filepaths.extend([os.path.join(root, f) for f in files])
                    continue
                else:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r") as f:
                            file_contents = f.read()

                        click.echo(file_path)
                        click.echo("---")
                        click.echo(file_contents)
                        click.echo()
                        click.echo("---")
                    except UnicodeDecodeError:
                        warning_message = (
                            f"Warning: Skipping file {file_path} due to UnicodeDecodeError"
                        )
                        click.echo(click.style(warning_message, fg="red"), err=True)

        if output_format == "claude-xml":
            xml_root = xml_formatter.create_document_xml(filepaths, base64_encode_binary=False)
            click.echo(xml_formatter.write_document_xml(xml_root))
        elif output_format == "claude-xml-b64":
            xml_root = xml_formatter.create_document_xml(filepaths, base64_encode_binary=True)
            click.echo(xml_formatter.write_document_xml(xml_root))

@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
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
@click.option(
    "ignore_patterns",
    "--ignore",
    multiple=True,
    default=[],
    help="List of patterns to ignore",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["default", "claude-xml", "claude-xml-b64"]),
    default="default",
    help="Output format",
)
@click.version_option()
def cli(paths, include_hidden, ignore_gitignore, ignore_patterns, output_format):
    """
    Takes one or more paths to files or directories and outputs every file,
    recursively, each one preceded with its filename like this:

    path/to/file.py
    ----
    Contents of file.py goes here

    ---
    path/to/file2.py
    ---
    ...
    """
    gitignore_rules = []
    for path in paths:
        if not os.path.exists(path):
            raise click.BadArgumentUsage(f"Path does not exist: {path}")
        if not ignore_gitignore:
            gitignore_rules.extend(read_gitignore(os.path.dirname(path)))
        process_path(
            path, include_hidden, ignore_gitignore, gitignore_rules, ignore_patterns, output_format
        )