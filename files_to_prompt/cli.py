import os
from fnmatch import fnmatch

import click
from datetime import datetime, timedelta

global_index = 1
current_time = datetime.now()  # Track current time for date comparison filters


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


def parse_time_delta(delta_str):
    """
    Parse a string in the format "30s", "30m", "30h", "30d", etc. into a timedelta object.

    Args:
        delta_str (str): The string to parse.

    Returns:
        timedelta: The parsed timedelta object.

    Raises:
        ValueError: If the input string is invalid.
    """
    import re

    match = re.match(r"(\d+)([smhd])", delta_str)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if unit == "s":
            return timedelta(seconds=value)
        elif unit == "m":
            return timedelta(minutes=value)
        elif unit == "h":
            return timedelta(hours=value)
        elif unit == "d":
            return timedelta(days=value)
    raise ValueError("Invalid time delta string")


def filter_by_mtime(path, mtime_delta):
    """
    Filter files based on their modification time.

    Args:
        path (str): The file path to check.
        mtime_delta (timedelta): The time delta to filter by.

    Returns:
        bool: True if the file's modification time is within the delta, False otherwise.
    """
    file_mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return current_time - file_mtime <= mtime_delta


def print_path(writer, path, content, xml):
    if xml:
        print_as_xml(writer, path, content)
    else:
        print_default(writer, path, content)


def print_default(writer, path, content):
    writer(path)
    writer("---")
    writer(content)
    writer("")
    writer("---")


def print_as_xml(writer, path, content):
    global global_index
    writer(f'<document index="{global_index}">')
    writer(f"<source>{path}</source>")
    writer("<document_content>")
    writer(content)
    writer("</document_content>")
    writer("</document>")
    global_index += 1


def process_path(
    path,
    include_hidden,
    ignore_gitignore,
    gitignore_rules,
    ignore_patterns,
    mtime_delta,
    writer,
    claude_xml,
):
    if os.path.isfile(path):
        if mtime_delta is not None and not filter_by_mtime(path, mtime_delta):
            return  # skip file if it's older than specified delta
        try:
            with open(path, "r") as f:
                print_path(writer, path, f.read(), claude_xml)
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

            if mtime_delta is not None:
                files = [
                    f
                    for f in files
                    if filter_by_mtime(os.path.join(root, f), mtime_delta)
                ]

            for file in sorted(files):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        print_path(writer, file_path, f.read(), claude_xml)
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
    "--mtime",
    type=str,
    default=None,
    help="Filter files modified in the last 'delta' time. Examples: 30s, 30m, 30h, 30d",
)
@click.option(
    "output_file",
    "-o",
    "--output",
    type=click.Path(writable=True),
    help="Output to a file instead of stdout",
)
@click.option(
    "claude_xml",
    "-c",
    "--cxml",
    is_flag=True,
    help="Output in XML-ish format suitable for Claude's long context window.",
)
@click.version_option()
def cli(
    paths,
    include_hidden,
    ignore_gitignore,
    ignore_patterns,
    mtime,
    output_file,
    claude_xml,
):
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
    writer = click.echo
    fp = None

    if output_file:
        fp = open(output_file, "w")
        writer = lambda s: print(s, file=fp)

    mtime_delta = None
    if mtime is not None:
        try:
            mtime_delta = parse_time_delta(mtime)
        except ValueError as e:
            raise click.BadOptionUsage("--mtime", str(e))

    for path in paths:
        if not os.path.exists(path):
            raise click.BadArgumentUsage(f"Path does not exist: {path}")
        if not ignore_gitignore:
            gitignore_rules.extend(read_gitignore(os.path.dirname(path)))
        if claude_xml and path == paths[0]:
            writer("<documents>")
        process_path(
            path,
            include_hidden,
            ignore_gitignore,
            gitignore_rules,
            ignore_patterns,
            mtime_delta,
            writer,
            claude_xml,
        )
    if claude_xml:
        writer("</documents>")
    if fp:
        fp.close()
