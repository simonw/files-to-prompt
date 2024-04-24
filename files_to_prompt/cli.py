import os
import click
from fnmatch import fnmatch
import tiktoken

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
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return []

def read_ftpignore():
    # Path to the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ftpignore_path = os.path.join(script_dir, ".ftpignore")
    if os.path.isfile(ftpignore_path):
        with open(ftpignore_path, "r") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return []

def process_path(path, include_hidden, ignore_gitignore, gitignore_rules, ignore_patterns, output_file):
    with open(output_file, "w") as output:
        if os.path.isfile(path):
            try:
                with open(path, "r") as f:
                    file_contents = f.read()
                output.write(f"{path}\n---\n{file_contents}\n\n---\n")
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
                    dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), gitignore_rules)]
                    files = [f for f in files if not should_ignore(os.path.join(root, f), gitignore_rules)]

                dirs[:] = [d for d in dirs if not any(fnmatch(d, pattern) for pattern in ignore_patterns)]
                files = [f for f in files if not any(fnmatch(f, pattern) for pattern in ignore_patterns)]

                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r") as f:
                            file_contents = f.read()
                        output.write(f"{file_path}\n---\n{file_contents}\n\n---\n")
                    except UnicodeDecodeError:
                        warning_message = f"Warning: Skipping file {file_path} due to UnicodeDecodeError"
                        click.echo(click.style(warning_message, fg="red"), err=True)

def count_tokens(file_name):
    enc = tiktoken.get_encoding("cl100k_base")
    try:
        with open(file_name, 'r') as file:
            content = file.read()
        tokens = enc.decode(enc.encode(content))
        return len(tokens)
    except FileNotFoundError:
        click.echo(click.style(f"Error: File not found - {file_name}", fg="red"), err=True)
    except Exception as e:
        click.echo(click.style(f"Error processing file {file_name}: {str(e)}", fg="red"), err=True)

@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("--include-hidden", is_flag=True, help="Include files and folders starting with .")
@click.option("--ignore-gitignore", is_flag=True, help="Ignore .gitignore files and include all files")
@click.option("ignore_patterns", "--ignore", multiple=True, default=[], help="List of patterns to ignore")
@click.option("--output", default="output.txt", help="Output file to write the results to")
@click.option("--count-tokens", "count_tokens_path", type=click.Path(exists=True), help="Count the number of tokens in the specified file")
@click.version_option()
def cli(paths, include_hidden, ignore_gitignore, ignore_patterns, output, count_tokens_path):
    if count_tokens_path:
        token_count = count_tokens(count_tokens_path)
        click.echo(f"Token count for {count_tokens_path}: {token_count}")
        return

    ftpignore_rules = read_ftpignore()  # Always include these rules
    output_file = os.path.join(os.getcwd(), output)
    for path in paths:
        ignore_rules = list(ftpignore_rules)  # Start with the global .ftpignore rules
        if not os.path.exists(path):
            raise click.BadArgumentUsage(f"Path does not exist: {path}")
        if not ignore_gitignore:
            ignore_rules.extend(read_gitignore(os.path.dirname(path)))  # Add .gitignore rules from the path's directory
        process_path(path, include_hidden, ignore_gitignore, ignore_rules, ignore_patterns, output_file)
