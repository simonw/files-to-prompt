import os
import sys
from fnmatch import fnmatch
from collections import defaultdict
from pathlib import Path

import click

global_index = 1

# Token counting function with tiktoken fallback
def count_tokens(content):
    """Count tokens with tiktoken fallback to char approximation."""
    try:
        import tiktoken
        # Use cl100k_base encoding (GPT-3.5/4)
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(content))
    except ImportError:
        # Fallback: chars/4 approximation
        return len(content) // 4


class FileStats:
    """Collect statistics about processed files."""
    
    def __init__(self):
        self.file_tokens = {}  # path -> token_count
        self.file_lines = {}   # path -> line_count
        self.total_lines = 0
        self.files_processed = 0
        self.files_ignored = 0
        
    def add_file(self, path, content):
        """Add a file's statistics."""
        tokens = count_tokens(content)
        lines = content.count('\n') + 1
        
        self.file_tokens[path] = tokens
        self.file_lines[path] = lines
        self.total_lines += lines
        self.files_processed += 1
        
    def increment_ignored(self):
        """Increment the ignored file counter."""
        self.files_ignored += 1
        
    def get_top_files(self, n=20):
        """Return top N files by token count."""
        sorted_files = sorted(self.file_tokens.items(), key=lambda x: x[1], reverse=True)
        return sorted_files[:n]
        
    def get_directory_summary(self):
        """Aggregate token counts by first-level directories."""
        dir_tokens = defaultdict(int)
        
        for path, tokens in self.file_tokens.items():
            # Normalize path separators
            path_parts = Path(path).parts
            
            if len(path_parts) > 1:
                # Use first directory in path
                first_dir = path_parts[0]
                dir_tokens[first_dir] += tokens
            else:
                # File in root
                dir_tokens["(root)"] += tokens
                
        # Sort by token count descending
        return sorted(dir_tokens.items(), key=lambda x: x[1], reverse=True)
        
    def get_total_tokens(self):
        """Get total token count across all files."""
        return sum(self.file_tokens.values())
        
    def print_summary(self, writer=None):
        """Print the statistics summary to stderr."""
        if writer is None:
            writer = lambda s: click.echo(s, err=True)
            
        total_tokens = self.get_total_tokens()
        
        writer("\nSummary:")
        writer("========")
        writer(f"Files processed: {self.files_processed:,}")
        writer(f"Files ignored: {self.files_ignored:,}")
        writer(f"Total tokens: {total_tokens:,}")
        writer(f"Total lines: {self.total_lines:,}")
        
        # Top files
        writer("\nTop 20 files by token count:")
        for path, tokens in self.get_top_files(20):
            writer(f"{tokens:8,}  {path}")
            
        # Directory summary
        writer("\nToken count by directory:")
        dir_summary = self.get_directory_summary()
        for dir_name, tokens in dir_summary:
            percentage = (tokens / total_tokens * 100) if total_tokens > 0 else 0
            writer(f"{dir_name:15} {tokens:8,} tokens ({percentage:4.1f}%)")


EXT_TO_LANG = {
    "py": "python",
    "c": "c",
    "cpp": "cpp",
    "java": "java",
    "js": "javascript",
    "ts": "typescript",
    "html": "html",
    "css": "css",
    "xml": "xml",
    "json": "json",
    "yaml": "yaml",
    "yml": "yaml",
    "sh": "bash",
    "rb": "ruby",
}


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


def add_line_numbers(content):
    lines = content.splitlines()

    padding = len(str(len(lines)))

    numbered_lines = [f"{i + 1:{padding}}  {line}" for i, line in enumerate(lines)]
    return "\n".join(numbered_lines)


def print_path(writer, path, content, cxml, markdown, line_numbers):
    if cxml:
        print_as_xml(writer, path, content, line_numbers)
    elif markdown:
        print_as_markdown(writer, path, content, line_numbers)
    else:
        print_default(writer, path, content, line_numbers)


def print_default(writer, path, content, line_numbers):
    writer(path)
    writer("---")
    if line_numbers:
        content = add_line_numbers(content)
    writer(content)
    writer("")
    writer("---")


def print_as_xml(writer, path, content, line_numbers):
    global global_index
    writer(f'<document index="{global_index}">')
    writer(f"<source>{path}</source>")
    writer("<document_content>")
    if line_numbers:
        content = add_line_numbers(content)
    writer(content)
    writer("</document_content>")
    writer("</document>")
    global_index += 1


def print_as_markdown(writer, path, content, line_numbers):
    lang = EXT_TO_LANG.get(path.split(".")[-1], "")
    # Figure out how many backticks to use
    backticks = "```"
    while backticks in content:
        backticks += "`"
    writer(path)
    writer(f"{backticks}{lang}")
    if line_numbers:
        content = add_line_numbers(content)
    writer(content)
    writer(f"{backticks}")


def process_path(
    path,
    extensions,
    include_hidden,
    ignore_files_only,
    ignore_gitignore,
    gitignore_rules,
    ignore_patterns,
    writer,
    claude_xml,
    markdown,
    line_numbers=False,
    stats=None,
):
    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                content = f.read()
                print_path(writer, path, content, claude_xml, markdown, line_numbers)
                if stats:
                    stats.add_file(path, content)
        except UnicodeDecodeError:
            warning_message = f"Warning: Skipping file {path} due to UnicodeDecodeError"
            click.echo(click.style(warning_message, fg="red"), err=True)
            if stats:
                stats.increment_ignored()
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
                if not ignore_files_only:
                    dirs[:] = [
                        d
                        for d in dirs
                        if not any(fnmatch(d, pattern) for pattern in ignore_patterns)
                    ]
                files = [
                    f
                    for f in files
                    if not any(fnmatch(f, pattern) for pattern in ignore_patterns)
                ]

            if extensions:
                files = [f for f in files if f.endswith(extensions)]

            for file in sorted(files):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        content = f.read()
                        print_path(
                            writer,
                            file_path,
                            content,
                            claude_xml,
                            markdown,
                            line_numbers,
                        )
                        if stats:
                            stats.add_file(file_path, content)
                except UnicodeDecodeError:
                    warning_message = (
                        f"Warning: Skipping file {file_path} due to UnicodeDecodeError"
                    )
                    click.echo(click.style(warning_message, fg="red"), err=True)
                    if stats:
                        stats.increment_ignored()


def read_paths_from_stdin(use_null_separator):
    if sys.stdin.isatty():
        # No ready input from stdin, don't block for input
        return []

    stdin_content = sys.stdin.read()
    if use_null_separator:
        paths = stdin_content.split("\0")
    else:
        paths = stdin_content.split()  # split on whitespace
    return [p for p in paths if p]


@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("extensions", "-e", "--extension", multiple=True)
@click.option(
    "--include-hidden",
    is_flag=True,
    help="Include files and folders starting with .",
)
@click.option(
    "--ignore-files-only",
    is_flag=True,
    help="--ignore option only ignores files",
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
@click.option(
    "markdown",
    "-m",
    "--markdown",
    is_flag=True,
    help="Output Markdown with fenced code blocks",
)
@click.option(
    "line_numbers",
    "-n",
    "--line-numbers",
    is_flag=True,
    help="Add line numbers to the output",
)
@click.option(
    "--null",
    "-0",
    is_flag=True,
    help="Use NUL character as separator when reading from stdin",
)
@click.option(
    "--stats",
    is_flag=True,
    help="Show statistics about processed files (file count, token count, etc.)",
)
@click.version_option()
def cli(
    paths,
    extensions,
    include_hidden,
    ignore_files_only,
    ignore_gitignore,
    ignore_patterns,
    output_file,
    claude_xml,
    markdown,
    line_numbers,
    null,
    stats,
):
    """
    Takes one or more paths to files or directories and outputs every file,
    recursively, each one preceded with its filename like this:

    \b
        path/to/file.py
        ----
        Contents of file.py goes here
        ---
        path/to/file2.py
        ---
        ...

    If the `--cxml` flag is provided, the output will be structured as follows:

    \b
        <documents>
        <document path="path/to/file1.txt">
        Contents of file1.txt
        </document>
        <document path="path/to/file2.txt">
        Contents of file2.txt
        </document>
        ...
        </documents>

    If the `--markdown` flag is provided, the output will be structured as follows:

    \b
        path/to/file1.py
        ```python
        Contents of file1.py
        ```
    """
    # Reset global_index for pytest
    global global_index
    global_index = 1

    # Read paths from stdin if available
    stdin_paths = read_paths_from_stdin(use_null_separator=null)

    # Combine paths from arguments and stdin
    paths = [*paths, *stdin_paths]

    gitignore_rules = []
    writer = click.echo
    fp = None
    if output_file:
        fp = open(output_file, "w", encoding="utf-8")
        writer = lambda s: print(s, file=fp)
    
    # Initialize stats collector if requested
    file_stats = FileStats() if stats else None
    for path in paths:
        if not os.path.exists(path):
            raise click.BadArgumentUsage(f"Path does not exist: {path}")
        if not ignore_gitignore:
            gitignore_rules.extend(read_gitignore(os.path.dirname(path)))
        if claude_xml and path == paths[0]:
            writer("<documents>")
        process_path(
            path,
            extensions,
            include_hidden,
            ignore_files_only,
            ignore_gitignore,
            gitignore_rules,
            ignore_patterns,
            writer,
            claude_xml,
            markdown,
            line_numbers,
            file_stats,
        )
    if claude_xml:
        writer("</documents>")
    if fp:
        fp.close()
    
    # Print statistics summary to stderr if requested
    if file_stats:
        file_stats.print_summary()
