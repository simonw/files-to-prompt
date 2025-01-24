import os
from fnmatch import fnmatch
from datetime import datetime, timedelta

import click

class FileProcessor:
    def __init__(self):
        self.global_index = 1
        self.current_time = datetime.now()

    def should_ignore(self, path, gitignore_rules):
        basename = os.path.basename(path)
        for rule in gitignore_rules:
            if fnmatch(basename, rule):
                return True
            if os.path.isdir(path) and fnmatch(basename + "/", rule):
                return True
        return False

    def read_gitignore(self, path):
        gitignore_path = os.path.join(path, ".gitignore")
        if os.path.isfile(gitignore_path):
            with open(gitignore_path, "r") as f:
                return [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]
        return []

    def parse_time_delta(self, delta_str):
        """Parse a string like "30s", "1h", "7d" into a timedelta object."""
        import re

        match = re.match(r"(\d+)([smhd])", delta_str)
        if not match:
            raise ValueError(
                "Invalid time delta string. Use format like 30s, 1m, 2h, 7d"
            )
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
        return None  # Should not happen due to regex, but for completeness

    def is_modified_within_delta(self, path, mtime_delta):
        """Check if a file was modified within the specified timedelta."""
        file_mtime = datetime.fromtimestamp(os.path.getmtime(path))
        return self.current_time - file_mtime <= mtime_delta

    def format_output(self, path, content, llm_format=None):
        if llm_format == "claude":
            return self._format_as_xml(path, content)
        elif llm_format == "openai":
            return self._format_markdown(path, content)
        elif llm_format == "gemini":
            return self._format_gemini(path, content)
        else:
            return self._format_default(path, content)

    def _format_default(self, path, content):
        return f"{path}\n---\n{content}\n\n---\n"

    def _format_as_xml(self, path, content):
        output = (
            f'<document index="{self.global_index}">\n'
            f"<source>{path}</source>\n"
            "<document_content>\n"
            f"{content}\n"
            "</document_content>\n"
            "</document>\n"
        )
        self.global_index += 1
        return output

    def _format_markdown(self, path, content):
        return f"## {path}\n```\n{content}\n```\n\n"

    def _format_gemini(self, path, content):
        return f"## File: {path}\n```\n{content}\n```\n\n"

    def process_file(self, file_path, writer, llm_format):
        try:
            with open(file_path, "r") as f:
                content = f.read()
                writer(self.format_output(file_path, content, llm_format))
        except UnicodeDecodeError:
            warning_message = (
                f"Warning: Skipping file {file_path} due to UnicodeDecodeError"
            )
            click.echo(click.style(warning_message, fg="red"), err=True)

    def process_directory(
        self,
        path,
        extensions,
        include_hidden,
        ignore_gitignore,
        gitignore_rules,
        ignore_patterns,
        include_patterns,
        mtime_delta,
        writer,
        llm_format,
    ):
        for root, dirs, files in os.walk(path):
            # Filter directories
            dirs[:] = [
                d
                for d in dirs
                if (include_hidden or not d.startswith("."))
                and (ignore_gitignore or not self.should_ignore(os.path.join(root, d), gitignore_rules))
            ]

            # Filter files
            files = sorted([
                f
                for f in files
                if (include_hidden or not f.startswith("."))
                and (ignore_gitignore or not self.should_ignore(os.path.join(root, f), gitignore_rules))
                and (not extensions or f.endswith(extensions))
                and (not ignore_patterns or not any(fnmatch(f, pattern) for pattern in ignore_patterns))
                and (not include_patterns or any(fnmatch(f, pattern) for pattern in include_patterns))
                and (mtime_delta is None or self.is_modified_within_delta(os.path.join(root, f), mtime_delta))
            ])

            for file in files:
                self.process_file(os.path.join(root, file), writer, llm_format)

    def process_path(
        self,
        path,
        extensions,
        include_hidden,
        ignore_gitignore,
        ignore_patterns,
        include_patterns,
        mtime_delta,
        writer,
        llm_format,
    ):
        if os.path.isfile(path):
            if (not include_patterns or any(fnmatch(os.path.basename(path), pattern) for pattern in include_patterns)) and \
               (mtime_delta is None or self.is_modified_within_delta(path, mtime_delta)):
                self.process_file(path, writer, llm_format)
        elif os.path.isdir(path):
            if not ignore_gitignore:
                gitignore_rules = self.read_gitignore(path)
            else:
                gitignore_rules = []
            self.process_directory(
                path,
                extensions,
                include_hidden,
                ignore_gitignore,
                gitignore_rules,
                ignore_patterns,
                include_patterns,
                mtime_delta,
                writer,
                llm_format,
            )

def print_output(s, file=None):
    print(s, file=file)

@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("-e", "--extension", multiple=True, help="Filter by file extension.")
@click.option(
    "--include-hidden", is_flag=True, help="Include hidden files and directories."
)
@click.option(
    "--ignore-gitignore", is_flag=True, help="Ignore .gitignore rules."
)
@click.option("--ignore", multiple=True, help="Ignore files matching this pattern.")
@click.option("--include", multiple=True, help="Include files matching this pattern.")
@click.option(
    "--mtime",
    type=str,
    help="Filter files modified within the given time (e.g., 30s, 1h, 7d).",
)
@click.option("-o", "--output", type=click.Path(writable=True), help="Output to file.")
@click.option(
    "--llm-format",
    type=click.Choice(["claude", "openai", "gemini"]),
    help="Format output for a specific LLM.",
)
@click.version_option()
def cli(
    paths,
    extension,
    include_hidden,
    ignore_gitignore,
    ignore,
    include,
    mtime,
    output,
    llm_format,
):
    """
    Concatenates the content of files into a single output, optimized for LLMs.

    Specify one or more paths to files or directories.
    Recursively outputs the content of each file,
    optionally formatted for specific LLMs.

    Example (default output):

    \b
    path/to/file.py
    ---
    Contents of file.py goes here

    ---
    path/to/file2.py
    ---
    ...

    Use --llm-format to structure the output for specific LLMs.
    """
    processor = FileProcessor()
    writer = click.echo
    fp = None

    if output:
        fp = open(output, "w")
        def writer(s):
            print_output(s, file=fp)

    mtime_delta = None
    if mtime:
        try:
            mtime_delta = processor.parse_time_delta(mtime)
        except ValueError as e:
            raise click.BadOptionUsage("--mtime", str(e))

    if llm_format == "claude":
        writer("<documents>")

    for path in paths:
        if not os.path.exists(path):
            raise click.BadArgumentUsage(f"Path does not exist: {path}")
        processor.process_path(
            path,
            extension,
            include_hidden,
            ignore_gitignore,
            ignore,
            include,
            mtime_delta,
            writer,
            llm_format,
        )

    if llm_format == "claude":
        writer("</documents>")

    if fp:
        fp.close()

if __name__ == "__main__":
    cli()