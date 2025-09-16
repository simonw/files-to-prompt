# files-to-prompt

[![PyPI](https://img.shields.io/pypi/v/files-to-prompt.svg)](https://pypi.org/project/files-to-prompt/)
[![Changelog](https://img.shields.io/github/v/release/simonw/files-to-prompt?include_prereleases&label=changelog)](https://github.com/simonw/files-to-prompt/releases)
[![Tests](https://github.com/simonw/files-to-prompt/actions/workflows/test.yml/badge.svg)](https://github.com/simonw/files-to-prompt/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/files-to-prompt/blob/master/LICENSE)

Concatenate a directory full of files into a single prompt for use with LLMs

For background on this project see [Building files-to-prompt entirely using Claude 3 Opus](https://simonwillison.net/2024/Apr/8/files-to-prompt/).

## Installation

Install this tool using `pip`:

```bash
pip install files-to-prompt
```

## Usage

To use `files-to-prompt`, provide the path to one or more files or directories you want to process:

```bash
files-to-prompt path/to/file_or_directory [path/to/another/file_or_directory ...]
```

This will output the contents of every file, with each file preceded by its relative path and separated by `---`.

### Options

- `-e/--extension <extension>`: Only include files with the specified extension. Can be used multiple times.

  ```bash
  files-to-prompt path/to/directory -e txt -e md
  ```

- `--include-hidden`: Include files and folders starting with `.` (hidden files and directories).

  ```bash
  files-to-prompt path/to/directory --include-hidden
  ```

- `--ignore <pattern>`: Specify one or more patterns to ignore. Can be used multiple times. Patterns may match file names and directory names, unless you also specify `--ignore-files-only`. Pattern syntax uses [fnmatch](https://docs.python.org/3/library/fnmatch.html), which supports `*`, `?`, `[anychar]`, `[!notchars]` and `[?]` for special character literals.
  ```bash
  files-to-prompt path/to/directory --ignore "*.log" --ignore "temp*"
  ```

- `--ignore-files-only`: Include directory paths which would otherwise be ignored by an `--ignore` pattern.

  ```bash
  files-to-prompt path/to/directory --ignore-files-only --ignore "*dir*"
  ```

- `--ignore-gitignore`: Ignore `.gitignore` files and include all files.

  ```bash
  files-to-prompt path/to/directory --ignore-gitignore
  ```

- `-c/--cxml`: Output in Claude XML format.

  ```bash
  files-to-prompt path/to/directory --cxml
  ```

- `-m/--markdown`: Output as Markdown with fenced code blocks.

  ```bash
  files-to-prompt path/to/directory --markdown
  ```

- `-o/--output <file>`: Write the output to a file instead of printing it to the console.

  ```bash
  files-to-prompt path/to/directory -o output.txt
  ```

- `-n/--line-numbers`: Include line numbers in the output.

  ```bash
  files-to-prompt path/to/directory -n
  ```
  Example output:
  ```
  files_to_prompt/cli.py
  ---
    1  import os
    2  from fnmatch import fnmatch
    3
    4  import click
    ...
  ```

- `-0/--null`: Use NUL character as separator when reading paths from stdin. Useful when filenames may contain spaces.

  ```bash
  find . -name "*.py" -print0 | files-to-prompt --null
  ```

- `--since <REF>`: Only include files changed since a Git revision (commit SHA, tag, or branch).

  * Default scope is **working**: commits after `REF` + staged + unstaged + untracked (Git ignores respected).
  * Paths given on the command line (or via stdin) further restrict the set.
  * In this mode, `--ignore-gitignore` is ignored.

  ```bash
  files-to-prompt --since HEAD
  files-to-prompt --since v1.2.0 -e py
  files-to-prompt --since main src tests
  ```

- `--since-scope <working|committed|staged>`: Control what "changed since REF" means (default: `working`).

  * `working`: commits after `REF` + staged + unstaged + untracked
  * `committed`: only commits after `REF` (no staged/unstaged/untracked)
  * `staged`: only index vs `REF` (no unstaged/untracked)

  ```bash
  files-to-prompt --since v1.2.0 --since-scope committed
  files-to-prompt --since HEAD --since-scope staged
  ```

### Example

Suppose you have a directory structure like this:

```
my_directory/
├── file1.txt
├── file2.txt
├── .hidden_file.txt
├── temp.log
└── subdirectory/
    └── file3.txt
```

Running `files-to-prompt my_directory` will output:

```
my_directory/file1.txt
---
Contents of file1.txt
---
my_directory/file2.txt
---
Contents of file2.txt
---
my_directory/subdirectory/file3.txt
---
Contents of file3.txt
---
```

If you run `files-to-prompt my_directory --include-hidden`, the output will also include `.hidden_file.txt`:

```
my_directory/.hidden_file.txt
---
Contents of .hidden_file.txt
---
...
```

If you run `files-to-prompt my_directory --ignore "*.log"`, the output will exclude `temp.log`:

```
my_directory/file1.txt
---
Contents of file1.txt
---
my_directory/file2.txt
---
Contents of file2.txt
---
my_directory/subdirectory/file3.txt
---
Contents of file3.txt
---
```

If you run `files-to-prompt my_directory --ignore "sub*"`, the output will exclude all files in `subdirectory/` (unless you also specify `--ignore-files-only`):

```
my_directory/file1.txt
---
Contents of file1.txt
---
my_directory/file2.txt
---
Contents of file2.txt
---
```

### Reading from stdin

The tool can also read paths from standard input. This can be used to pipe in the output of another command:

```bash
# Find files modified in the last day
find . -mtime -1 | files-to-prompt
```

When using the `--null` (or `-0`) option, paths are expected to be NUL-separated (useful when dealing with filenames containing spaces):

```bash
find . -name "*.txt" -print0 | files-to-prompt --null
```

You can mix and match paths from command line arguments and stdin:

```bash
# Include files modified in the last day, and also include README.md
find . -mtime -1 | files-to-prompt README.md
```

**Notes for `--since`**: paths are repo-root-relative; deleted files are not emitted. Untracked files are included only with `--since-scope working`. Other filters (`-e/--extension`, `--ignore`, `--ignore-files-only`, `--include-hidden`) still apply.

### Claude XML Output

Anthropic has provided [specific guidelines](https://docs.anthropic.com/claude/docs/long-context-window-tips) for optimally structuring prompts to take advantage of Claude's extended context window.

To structure the output in this way, use the optional `--cxml` flag, which will produce output like this:

```xml
<documents>
<document index="1">
<source>my_directory/file1.txt</source>
<document_content>
Contents of file1.txt
</document_content>
</document>
<document index="2">
<source>my_directory/file2.txt</source>
<document_content>
Contents of file2.txt
</document_content>
</document>
</documents>
```

## --markdown fenced code block output

The `--markdown` option will output the files as fenced code blocks, which can be useful for pasting into Markdown documents.

```bash
files-to-prompt path/to/directory --markdown
```
The language tag will be guessed based on the filename.

If the code itself contains triple backticks the wrapper around it will use one additional backtick.

Example output:
`````
myfile.py
```python
def my_function():
    return "Hello, world!"
```
other.js
```javascript
function myFunction() {
    return "Hello, world!";
}
```
file_with_triple_backticks.md
````markdown
This file has its own
```
fenced code blocks
```
Inside it.
````
`````

## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:

```bash
cd files-to-prompt
python -m venv venv
source venv/bin/activate
```

Now install the dependencies and test dependencies:

```bash
pip install -e '.[test]'
```

To run the tests:

```bash
pytest
```
