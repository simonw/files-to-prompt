# files-to-prompt

[![PyPI](https://img.shields.io/pypi/v/files-to-prompt.svg)](https://pypi.org/project/files-to-prompt/)
[![Changelog](https://img.shields.io/github/v/release/simonw/files-to-prompt?include_prereleases&label=changelog)](https://github.com/simonw/files-to-prompt/releases)
[![Tests](https://github.com/simonw/files-to-prompt/actions/workflows/test.yml/badge.svg)](https://github.com/simonw/files-to-prompt/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/files-to-prompt/blob/master/LICENSE)

Concatenate a directory full of files into a single prompt for use with LLMs

## Installation

Install this tool using `pip`:
```bash
pip install files-to-prompt
```
## Usage

To use `files-to-prompt`, provide the path to the directory you want to process:

```bash
files-to-prompt path/to/directory
```

This will output the contents of every file in the directory and its subdirectories, with each file preceded by its relative path and separated by `---`.

### Options

- `--include-hidden`: Include files and folders starting with `.` (hidden files and directories).
  ```bash
  files-to-prompt path/to/directory --include-hidden
  ```

- `--ignore-gitignore`: Ignore `.gitignore` files and include all files.
  ```bash
  files-to-prompt path/to/directory --ignore-gitignore
  ```

### Example

Suppose you have a directory structure like this:

```
my_directory/
├── file1.txt
├── file2.txt
├── .hidden_file.txt
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
