import os
import click
from fnmatch import fnmatch
import io

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
    path, include_hidden, ignore_gitignore, gitignore_rules, ignore_patterns
):
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

def split_output(output, max_chars):
    parts = []
    current_part = io.StringIO()
    current_char_count = 0

    for line in output.splitlines(True):  # keepends=True to preserve newlines
        if current_char_count + len(line) > max_chars and current_char_count > 0:
            parts.append(current_part.getvalue())
            current_part = io.StringIO()
            current_char_count = 0
        
        current_part.write(line)
        current_char_count += len(line)

    if current_part.getvalue():
        parts.append(current_part.getvalue())

    return parts

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
    "--split",
    type=int,
    default=0,
    help="Split output into multiple files with specified maximum character count",
)
@click.version_option()
def cli(paths, include_hidden, ignore_gitignore, ignore_patterns, split):
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
    output = io.StringIO()

    for path in paths:
        if not os.path.exists(path):
            raise click.BadArgumentUsage(f"Path does not exist: {path}")
        if not ignore_gitignore:
            gitignore_rules.extend(read_gitignore(os.path.dirname(path)))
        
        # Redirect output to StringIO
        original_stdout = click.get_text_stream('stdout')
        click.get_current_context().obj = {'stdout': output}
        
        process_path(
            path, include_hidden, ignore_gitignore, gitignore_rules, ignore_patterns
        )
        
        # Restore original stdout
        click.get_current_context().obj = {'stdout': original_stdout}

    if split > 0:
        parts = split_output(output.getvalue(), split)
        for i, part in enumerate(parts):
            with open(f"output_part_{i+1}.txt", "w") as f:
                f.write(part)
        click.echo(f"Output split into {len(parts)} files.")
    else:
        click.echo(output.getvalue())

if __name__ == "__main__":
    cli()