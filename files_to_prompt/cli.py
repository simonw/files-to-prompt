import os
from fnmatch import fnmatch

import click

global_index = 1


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


def print_path(path, content, xml):
    if xml:
        print_as_xml(path, content)
    else:
        print_default(path, content)


def print_default(path, content):
    click.echo(path)
    click.echo("---")
    click.echo(content)
    click.echo()
    click.echo("---")


def print_as_xml(path, content):
    global global_index
    click.echo(f'<document index="{global_index}">')
    click.echo(f"<source>{path}</source>")
    click.echo("<document_content>")
    click.echo(content)
    click.echo("</document_content>")
    click.echo("</document>")
    global_index += 1


def process_path(
    path,
    include_hidden,
    ignore_gitignore,
    gitignore_rules,
    ignore_patterns,
    claude_xml,
):
    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                print_path(path, f.read(), claude_xml)
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

            for file in sorted(files):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        print_path(file_path, f.read(), claude_xml)
                except UnicodeDecodeError:
                    warning_message = (
                        f"Warning: Skipping file {file_path} due to UnicodeDecodeError"
                    )
                    click.echo(click.style(warning_message, fg="red"), err=True)


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
    "claude_xml",
    "-c",
    "--cxml",
    is_flag=True,
    help="Output in XML-ish format suitable for Claude's long context window.",
)
@click.version_option()
def cli(paths, include_hidden, ignore_gitignore, ignore_patterns, claude_xml):
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

    If the `--cxml` flag is provided, the output will be structured as follows:

    <documents>
    <document path="path/to/file1.txt">
    Contents of file1.txt
    </document>

    <document path="path/to/file2.txt">
    Contents of file2.txt
    </document>
    ...
    </documents>
    """
    # Reset global_index for pytest
    global global_index
    global_index = 1
    gitignore_rules = []
    for path in paths:
        if not os.path.exists(path):
            raise click.BadArgumentUsage(f"Path does not exist: {path}")
        if not ignore_gitignore:
            gitignore_rules.extend(read_gitignore(os.path.dirname(path)))
        if claude_xml and path == paths[0]:
            click.echo("<documents>")
        process_path(
            path,
            include_hidden,
            ignore_gitignore,
            gitignore_rules,
            ignore_patterns,
            claude_xml,
        )
    if claude_xml:
        click.echo("</documents>")
