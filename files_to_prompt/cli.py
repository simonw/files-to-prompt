import os
import sys
import subprocess
from fnmatch import fnmatch

import click

global_index = 1


def _run_git(args, cwd):
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return proc.stdout.strip()
    except FileNotFoundError:
        raise click.ClickException("git not found on PATH; --since requires Git")
    except subprocess.CalledProcessError as e:
        raise click.ClickException(e.stderr.strip() or e.stdout.strip() or str(e))


def _git_repo_root():
    inside = _run_git(["rev-parse", "--is-inside-work-tree"], os.getcwd())
    if inside != "true":
        raise click.ClickException(
            "The --since option requires running inside a Git repository"
        )
    return _run_git(["rev-parse", "--show-toplevel"], os.getcwd())


def _validate_git_ref(ref, repo_root):
    try:
        _run_git(["rev-parse", "--quiet", "--verify", f"{ref}^{{commit}}"], repo_root)
    except click.ClickException as e:
        raise click.ClickException(f"Invalid Git revision '{ref}'.")


def _git_changed_paths_since(ref, repo_root, scope="working"):
    tracked = set()

    if scope == "working":
        # tracked changes between REF and working tree
        diff_out = _run_git(["diff", "--name-only", ref, "--"], repo_root)
        tracked = set(line for line in diff_out.splitlines() if line)
    elif scope == "committed":
        # only commits after REF
        diff_out = _run_git(["diff", "--name-only", f"{ref}..HEAD", "--"], repo_root)
        tracked = set(line for line in diff_out.splitlines() if line)
    elif scope == "staged":
        # only what's staged in index relative to REF
        diff_out = _run_git(["diff", "--name-only", "--cached", ref, "--"], repo_root)
        tracked = set(line for line in diff_out.splitlines() if line)

    # untracked files only for working scope
    untracked = set()
    if scope == "working":
        untracked_out = _run_git(
            ["ls-files", "--others", "--exclude-standard"], repo_root
        )
        untracked = set(line for line in untracked_out.splitlines() if line)

    candidates = tracked | untracked
    # only existing files
    return {p for p in candidates if os.path.isfile(os.path.join(repo_root, p))}


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
):
    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                print_path(writer, path, f.read(), claude_xml, markdown, line_numbers)
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
                        f"Warning: Skipping file {file_path} due to UnicodeDecodeError"
                    )
                    click.echo(click.style(warning_message, fg="red"), err=True)


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
    "since_ref",
    "--since",
    metavar="REF",
    help=(
        "Only include files changed since this Git revision (commit/tag/branch). "
        "Paths given on the command line (or stdin) further restrict results. "
        "In this mode, --ignore-gitignore is ignored."
    ),
)
@click.option(
    "since_scope",
    "--since-scope",
    type=click.Choice(["working", "committed", "staged"]),
    default="working",
    show_default=True,
    help="Which changes to include relative to REF: 'working' = commits after REF + staged + unstaged + untracked; 'committed' = commits after REF; 'staged' = index vs REF.",
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
    since_ref,
    since_scope,
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

    # Handle --since specially
    if since_ref:
        if ignore_gitignore:
            click.echo(
                click.style(
                    "--ignore-gitignore is ignored with --since; Git's ignore rules always apply.",
                    fg="yellow",
                ),
                err=True,
            )
        repo_root = _git_repo_root()
        _validate_git_ref(since_ref, repo_root)
        changed = _git_changed_paths_since(since_ref, repo_root, since_scope)

        # restrict to explicit paths if given
        if paths:
            abs_paths = [os.path.abspath(p) for p in paths]
            changed = {
                rel
                for rel in changed
                if any(
                    os.path.commonpath([os.path.join(repo_root, rel), ap]) == ap
                    for ap in abs_paths
                )
            }

        # apply include_hidden / ignore / extensions filters
        rels = []
        for rel in sorted(changed):
            rel_norm = os.path.normpath(rel.replace("/", os.sep))
            if not include_hidden and any(
                part.startswith(".") for part in rel_norm.split(os.sep)
            ):
                continue
            if extensions and not rel.endswith(tuple(extensions)):
                continue
            if ignore_patterns:
                base = os.path.basename(rel_norm)
                if ignore_files_only:
                    if any(fnmatch(base, pat) for pat in ignore_patterns):
                        continue
                else:
                    parts = rel_norm.split(os.sep)
                    if any(
                        fnmatch(part, pat) for part in parts for pat in ignore_patterns
                    ):
                        continue
            rels.append(rel)

        writer = click.echo
        fp = None
        if output_file:
            fp = open(output_file, "w", encoding="utf-8")
            writer = lambda s: print(s, file=fp)
        if claude_xml:
            writer("<documents>")
        for rel in rels:
            try:
                # For staged scope, read content from index; otherwise from working tree
                if since_scope == "staged":
                    content = _run_git(["show", f":{rel}"], repo_root)
                else:
                    abs_fp = os.path.join(repo_root, rel)
                    with open(abs_fp, "r") as f:
                        content = f.read()

                print_path(writer, rel, content, claude_xml, markdown, line_numbers)
            except (
                UnicodeDecodeError,
                subprocess.CalledProcessError,
                click.ClickException,
            ):
                warning_message = (
                    f"Warning: Skipping file {rel} due to Unicode/Git error"
                )
                click.echo(click.style(warning_message, fg="red"), err=True)
        if claude_xml:
            writer("</documents>")
        if fp:
            fp.close()
        return

    gitignore_rules = []
    writer = click.echo
    fp = None
    if output_file:
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
    if fp:
        fp.close()
