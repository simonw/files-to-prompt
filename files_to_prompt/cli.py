import os
import sys
from fnmatch import fnmatch
from io import StringIO
from pathlib import Path

import click

# Backwards compatibility patch for Click versions without 'mix_stderr' in CliRunner
from click.testing import CliRunner as _CliRunner  # type: ignore
from inspect import signature as _sig

if "mix_stderr" not in _sig(_CliRunner.__init__).parameters:
    _orig_init = _CliRunner.__init__  # type: ignore

    def _patched_init(self, *args, **kwargs):  # type: ignore
        # Drop the mix_stderr kwarg if provided
        kwargs.pop("mix_stderr", None)
        _orig_init(self, *args, **kwargs)

    _CliRunner.__init__ = _patched_init  # type: ignore


# TOML parsing: use stdlib tomllib on 3.11+, fall back to tomli elsewhere
import sys

if sys.version_info >= (3, 11):
    import tomllib  # type: ignore
else:  # pragma: no cover – executed on <3.11 only
    import tomli as tomllib  # type: ignore

global_index = 1

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


def find_project_config():
    """Find .files-to-prompt.toml in current or parent directories."""
    current = Path.cwd()
    while current != current.parent:
        config_path = current / ".files-to-prompt.toml"
        if config_path.exists():
            return config_path
        current = current.parent
    return None


def find_user_config():
    """Find user configuration file."""
    # Try ~/.config/files-to-prompt/config.toml first
    config_dir = Path.home() / ".config" / "files-to-prompt"
    config_path = config_dir / "config.toml"
    if config_path.exists():
        return config_path
    
    # Try ~/.files-to-prompt.toml as fallback
    alt_config = Path.home() / ".files-to-prompt.toml"
    if alt_config.exists():
        return alt_config
    
    return None


def load_toml_file(path):
    """Load a TOML file and return its contents."""
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        click.echo(f"Warning: Failed to load config from {path}: {e}", err=True)
        return {}


def merge_configs(configs):
    """Merge multiple config dictionaries, with first taking precedence."""
    result = {}
    # Process in reverse order so first config wins
    for config in reversed(configs):
        if "defaults" in config:
            defaults = config["defaults"]
            for key, value in defaults.items():
                if key == "ignore" and key in result:
                    # For ignore patterns, combine lists
                    result[key] = list(set(result[key] + value))
                else:
                    result[key] = value
    return result


def load_config(no_config=False):
    """Load configuration from files."""
    if no_config:
        return {}
    
    configs = []
    
    # Load user config first (lower precedence)
    user_config_path = find_user_config()
    if user_config_path:
        configs.append(load_toml_file(user_config_path))
    
    # Load project config (higher precedence)
    project_config_path = find_project_config()
    if project_config_path:
        configs.append(load_toml_file(project_config_path))
    
    return merge_configs(configs)


def norm_path(p: str) -> str:
    """Return path with forward slashes to ensure stable, cross-platform output."""
    return p.replace(os.sep, "/")


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
    p = norm_path(path)
    if cxml:
        print_as_xml(writer, p, content, line_numbers)
    elif markdown:
        print_as_markdown(writer, p, content, line_numbers)
    else:
        print_default(writer, p, content, line_numbers)


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
):
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                print_path(writer, path, f.read(), claude_xml, markdown, line_numbers)
        except UnicodeDecodeError:
            warning_message = f"Warning: Skipping file {norm_path(path)} due to UnicodeDecodeError"
            click.echo(warning_message)
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
                    with open(file_path, "r", encoding="utf-8") as f:
                        print_path(
                            writer,
                            file_path,
                            f.read(),
                            claude_xml,
                            markdown,
                            line_numbers,
                        )
                except UnicodeDecodeError:
                    warning_message = (
                        f"Warning: Skipping file {norm_path(file_path)} due to UnicodeDecodeError"
                    )
                    click.echo(warning_message)


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
    "copy_to_clipboard",
    "-C",
    "--copy",
    is_flag=True,
    help="Copy the output to clipboard instead of stdout",
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
    "--no-config",
    is_flag=True,
    help="Ignore configuration files and use only command-line options",
)
@click.version_option()
@click.pass_context
def cli(
    ctx,
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
    copy_to_clipboard,
    no_config,
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
    # ------------------------------------------------------------
    # Configuration handling (project/user TOML)
    # ------------------------------------------------------------
    # Load configuration
    config = load_config(no_config)

    # Helper to see if an option was set explicitly on command line
    def _was_set(param_name: str) -> bool:
        try:
            return ctx.get_parameter_source(param_name).name == "commandline"
        except AttributeError:
            # Older Click (<8.1) fallback – assume not provided
            return False

    # Apply config defaults where CLI did not explicitly set them
    if not extensions and "extensions" in config:
        extensions = tuple(config["extensions"])

    if not ignore_patterns and "ignore" in config:
        ignore_patterns = tuple(config["ignore"])
    elif ignore_patterns and "ignore" in config:
        ignore_patterns = tuple(set(ignore_patterns) | set(config.get("ignore", [])))

    if not _was_set("include_hidden"):
        include_hidden = config.get("include_hidden", include_hidden)
    if not _was_set("ignore_files_only"):
        ignore_files_only = config.get("ignore_files_only", ignore_files_only)
    if not _was_set("ignore_gitignore"):
        ignore_gitignore = config.get("ignore_gitignore", ignore_gitignore)
    if not _was_set("copy_to_clipboard"):
        copy_to_clipboard = config.get("copy", copy_to_clipboard)
    if not _was_set("claude_xml"):
        claude_xml = config.get("cxml", claude_xml)
    if not _was_set("markdown"):
        markdown = config.get("markdown", markdown)
    if not _was_set("line_numbers"):
        line_numbers = config.get("line_numbers", line_numbers)

    if not output_file and "output" in config:
        output_file = config["output"]

    # ------------------------------------------------------------
    # Main processing logic (existing behaviour)
    # ------------------------------------------------------------
    global global_index
    global_index = 1  # Reset for each invocation (esp. tests)

    # Combine CLI paths with any from stdin
    stdin_paths = read_paths_from_stdin(use_null_separator=null)
    paths = [*paths, *stdin_paths]

    # Handle copy vs output precedence
    if copy_to_clipboard and output_file:
        click.echo(
            "Note: -o/--output overrides -C/--copy; writing output to file only.",
            err=True,
        )
        copy_to_clipboard = False

    gitignore_rules: list[str] = []
    writer = click.echo
    fp = None  # type: ignore
    clipboard_buffer = None

    if copy_to_clipboard:
        clipboard_buffer = StringIO()
        writer = lambda s: print(s, file=clipboard_buffer)
    elif output_file:
        fp = open(output_file, "w", encoding="utf-8")
        writer = lambda s: print(s, file=fp)

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
        )
    if claude_xml:
        writer("</documents>")

    if copy_to_clipboard and clipboard_buffer is not None:
        content = clipboard_buffer.getvalue()
        try:
            import pyperclip  # type: ignore
        except ImportError as exc:
            raise click.ClickException(
                "The -C/--copy option requires the optional 'pyperclip' package. "
                "Install it with 'pip install files-to-prompt[clipboard]' or "
                "re-run without -C/--copy."
            ) from exc
        try:
            pyperclip.copy(content)
            click.echo("Output copied to clipboard")
        except Exception as e:  # pragma: no cover – platform specific
            suggestion = ""
            if sys.platform.startswith("linux"):
                suggestion = " (hint: install 'xclip' or 'xsel')"
            elif sys.platform == "darwin":
                suggestion = " (make sure the 'pbcopy' utility is available)"
            click.echo(
                f"Failed to copy to clipboard: {e}{suggestion}. Output follows:",
                err=True,
            )
            click.echo(content)

    if fp:
        fp.close()