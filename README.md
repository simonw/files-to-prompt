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

- `--ignore-gitignore`: Ignore `.gitignore` files and include all files.

  ```bash
  files-to-prompt path/to/directory --ignore-gitignore
  ```

- `--ignore <pattern>`: Specify one or more patterns to ignore. Can be used multiple times.
  ```bash
  files-to-prompt path/to/directory --ignore "*.log" --ignore "temp*"
  ```

- `c/--cxml`: Output in Claude XML format.

  ```bash
  files-to-prompt path/to/directory --cxml
  ```

- `-o/--output <file>`: Write the output to a file instead of printing it to the console.

  ```bash
  files-to-prompt path/to/directory -o output.txt
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
