import os
import click
from fnmatch import fnmatch
import xml.etree.ElementTree as ET
from xml.dom import minidom

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
    path, include_hidden, ignore_gitignore, gitignore_rules, ignore_patterns, use_xml
):
    files_elem = ET.Element("files") if use_xml else None

    def process_file(file_path):
        try:
            with open(file_path, "r") as f:
                file_contents = f.read()
            if use_xml:
                file_elem = ET.SubElement(files_elem, "file")
                file_elem.set("path", file_path)
                file_elem.text = file_contents
            else:
                click.echo(file_path)
                click.echo("---")
                click.echo(file_contents)
                click.echo()
                click.echo("---")
        except UnicodeDecodeError:
            warning_message = f"Warning: Skipping file {file_path} due to UnicodeDecodeError"
            click.echo(click.style(warning_message, fg="red"), err=True)

    if os.path.isfile(path):
        process_file(path)
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
                file_path = os.path.join(root, file)
                process_file(file_path)

    return files_elem

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
    "--xml",
    is_flag=True,
    help="Output the result in simple XML format",
)
@click.version_option()
def cli(paths, include_hidden, ignore_gitignore, ignore_patterns, xml):
    """
    Takes one or more paths to files or directories and outputs every file,
    recursively, each one preceded with its filename.

    If the --xml flag is used, the output will be in a simple XML format:

    <files>
      <file path="path/to/file.py">
        Contents of file.py goes here
      </file>
      <file path="path/to/file2.py">
        Contents of file2.py
      </file>
    </files>
    """
    gitignore_rules = []
    if xml:
        root = ET.Element("files")
        for path in paths:
            if not os.path.exists(path):
                raise click.BadArgumentUsage(f"Path does not exist: {path}")
            if not ignore_gitignore:
                gitignore_rules.extend(read_gitignore(os.path.dirname(path)))
            files_elem = process_path(
                path, include_hidden, ignore_gitignore, gitignore_rules, ignore_patterns, xml
            )
            root.extend(files_elem)
        
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        click.echo(xml_str)
    else:
        for path in paths:
            if not os.path.exists(path):
                raise click.BadArgumentUsage(f"Path does not exist: {path}")
            if not ignore_gitignore:
                gitignore_rules.extend(read_gitignore(os.path.dirname(path)))
            process_path(
                path, include_hidden, ignore_gitignore, gitignore_rules, ignore_patterns, xml
            )

if __name__ == "__main__":
    cli()
