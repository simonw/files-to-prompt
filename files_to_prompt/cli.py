import os
from fnmatch import fnmatch
import requests
import base64

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
    extensions,
    include_hidden,
    ignore_gitignore,
    gitignore_rules,
    ignore_patterns,
    writer,
    claude_xml,
):
    if os.path.isfile(path):
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

            if extensions:
                files = [f for f in files if f.endswith(extensions)]

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


def fetch_github_files(repo_url, path="", token=None):
    # Extract owner and repo from the URL
    parts = repo_url.rstrip('/').split('/')
    if len(parts) < 2:
        raise click.ClickException(f"Invalid GitHub repository URL: {repo_url}")
    owner, repo = parts[-2], parts[-1]
    if repo.endswith('.git'):
        repo = repo[:-4]

    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"Error fetching GitHub repository: {str(e)}")

    content = response.json()
    files = []

    if isinstance(content, list):
        for item in content:
            if item["type"] == "file":
                file_url = item["download_url"]
                try:
                    file_content = requests.get(file_url, headers=headers).text
                    files.append((item["path"], file_content))
                except requests.exceptions.RequestException as e:
                    click.echo(f"Warning: Failed to fetch file {item['path']}: {str(e)}", err=True)
            elif item["type"] == "dir":
                files.extend(fetch_github_files(repo_url, item["path"], token))
    elif isinstance(content, dict) and content["type"] == "file":
        file_url = content["download_url"]
        try:
            file_content = requests.get(file_url, headers=headers).text
            files.append((content["path"], file_content))
        except requests.exceptions.RequestException as e:
            click.echo(f"Warning: Failed to fetch file {content['path']}: {str(e)}", err=True)
    
    return files


@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True), required=False)
@click.option("--github-repo", help="GitHub repository URL (e.g., https://github.com/username/repo.git)")
@click.option("--github-path", default="", help="Path within the GitHub repository (default: entire repo)")
@click.option("--github-token", envvar="GITHUB_TOKEN", help="GitHub personal access token")
@click.option("extensions", "-e", "--extension", multiple=True)
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
    github_repo,
    github_path,
    github_token,
    extensions,
    include_hidden,
    ignore_gitignore,
    ignore_patterns,
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

    if claude_xml:
        writer("<documents>")

    if github_repo:
        try:
            github_files = fetch_github_files(github_repo, github_path, github_token)
            if not github_files:
                raise click.ClickException(f"No files found in the specified GitHub repository: {github_repo}")
            for file_path, content in github_files:
                if extensions and not any(file_path.endswith(ext) for ext in extensions):
                    continue
                if claude_xml:
                    print_as_xml(writer, file_path, content)
                else:
                    print_default(writer, file_path, content)
        except click.ClickException as e:
            click.echo(str(e), err=True)
            return
    elif paths:
        for path in paths:
            if not os.path.exists(path):
                raise click.BadArgumentUsage(f"Path does not exist: {path}")
            if not ignore_gitignore:
                gitignore_rules.extend(read_gitignore(os.path.dirname(path)))
            process_path(
                path,
                extensions,
                include_hidden,
                ignore_gitignore,
                gitignore_rules,
                ignore_patterns,
                writer,
                claude_xml,
            )
    else:
        click.echo("Please provide either local paths or a GitHub repository URL.", err=True)
        return

    if claude_xml:
        writer("</documents>")
    if fp:
        fp.close()