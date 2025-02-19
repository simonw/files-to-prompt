import os
import pytest
import re

from click.testing import CliRunner

from files_to_prompt.cli import cli


def filenames_from_cxml(cxml_string):
    "Return set of filenames from <source>...</source> tags"
    return set(re.findall(r"<source>(.*?)</source>", cxml_string))


def test_basic_functionality(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Contents of file2")

        result = runner.invoke(cli, ["test_dir"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "test_dir/file1.txt" in result.output
        assert "Contents of file1" in result.output
        assert "test_dir/file2.txt" in result.output
        assert "Contents of file2" in result.output


def test_include_hidden(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/.hidden.txt", "w") as f:
            f.write("Contents of hidden file")

        result = runner.invoke(cli, ["test_dir"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "test_dir/.hidden.txt" not in result.output

        result = runner.invoke(cli, ["test_dir", "--include-hidden"])
        assert result.exit_code == 0
        assert "test_dir/.hidden.txt" in result.output
        assert "Contents of hidden file" in result.output


def test_ignore_gitignore(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        os.makedirs("test_dir/nested_include")
        os.makedirs("test_dir/nested_ignore")
        with open("test_dir/.gitignore", "w") as f:
            f.write("ignored.txt")
        with open("test_dir/ignored.txt", "w") as f:
            f.write("This file should be ignored")
        with open("test_dir/included.txt", "w") as f:
            f.write("This file should be included")
        with open("test_dir/nested_include/included2.txt", "w") as f:
            f.write("This nested file should be included")
        with open("test_dir/nested_ignore/.gitignore", "w") as f:
            f.write("*")
        with open("test_dir/nested_ignore/nested_ignore.txt", "w") as f:
            f.write("This nested file should not be included")

        result = runner.invoke(cli, ["test_dir", "-c"])
        assert result.exit_code == 0
        filenames = filenames_from_cxml(result.output)

        assert filenames == {
            "test_dir/included.txt",
            "test_dir/nested_include/included2.txt",
        }

        result2 = runner.invoke(cli, ["test_dir", "-c", "--ignore-gitignore"])
        assert result2.exit_code == 0
        filenames2 = filenames_from_cxml(result2.output)

        assert filenames2 == {
            "test_dir/included.txt",
            "test_dir/ignored.txt",
            "test_dir/nested_include/included2.txt",
            "test_dir/nested_ignore/nested_ignore.txt",
        }


def test_multiple_paths(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir1")
        with open("test_dir1/file1.txt", "w") as f:
            f.write("Contents of file1")
        os.makedirs("test_dir2")
        with open("test_dir2/file2.txt", "w") as f:
            f.write("Contents of file2")
        with open("single_file.txt", "w") as f:
            f.write("Contents of single file")

        result = runner.invoke(cli, ["test_dir1", "test_dir2", "single_file.txt"])
        assert result.exit_code == 0
        assert "test_dir1/file1.txt" in result.output
        assert "Contents of file1" in result.output
        assert "test_dir2/file2.txt" in result.output
        assert "Contents of file2" in result.output
        assert "single_file.txt" in result.output
        assert "Contents of single file" in result.output


def test_ignore_patterns(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir", exist_ok=True)
        with open("test_dir/file_to_ignore.txt", "w") as f:
            f.write("This file should be ignored due to ignore patterns")
        with open("test_dir/file_to_include.txt", "w") as f:
            f.write("This file should be included")

        result = runner.invoke(cli, ["test_dir", "--ignore", "*.txt"])
        assert result.exit_code == 0
        assert "test_dir/file_to_ignore.txt" not in result.output
        assert "This file should be ignored due to ignore patterns" not in result.output
        assert "test_dir/file_to_include.txt" not in result.output

        os.makedirs("test_dir/test_subdir", exist_ok=True)
        with open("test_dir/test_subdir/any_file.txt", "w") as f:
            f.write("This entire subdirectory should be ignored due to ignore patterns")
        result = runner.invoke(cli, ["test_dir", "--ignore", "*subdir*"])
        assert result.exit_code == 0
        assert "test_dir/test_subdir/any_file.txt" not in result.output
        assert (
            "This entire subdirectory should be ignored due to ignore patterns"
            not in result.output
        )
        assert "test_dir/file_to_include.txt" in result.output
        assert "This file should be included" in result.output
        assert "This file should be included" in result.output

        result = runner.invoke(
            cli, ["test_dir", "--ignore", "*subdir*", "--ignore-files-only"]
        )
        assert result.exit_code == 0
        assert "test_dir/test_subdir/any_file.txt" in result.output

        result = runner.invoke(cli, ["test_dir", "--ignore", ""])


def test_specific_extensions(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        # Write one.txt one.py two/two.txt two/two.py three.md
        os.makedirs("test_dir/two")
        with open("test_dir/one.txt", "w") as f:
            f.write("This is one.txt")
        with open("test_dir/one.py", "w") as f:
            f.write("This is one.py")
        with open("test_dir/two/two.txt", "w") as f:
            f.write("This is two/two.txt")
        with open("test_dir/two/two.py", "w") as f:
            f.write("This is two/two.py")
        with open("test_dir/three.md", "w") as f:
            f.write("This is three.md")

        # Try with -e py -e md
        result = runner.invoke(cli, ["test_dir", "-e", "py", "-e", "md"])
        assert result.exit_code == 0
        assert ".txt" not in result.output
        assert "test_dir/one.py" in result.output
        assert "test_dir/two/two.py" in result.output
        assert "test_dir/three.md" in result.output


def test_mixed_paths_with_options(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/.gitignore", "w") as f:
            f.write("ignored_in_gitignore.txt\n.hidden_ignored_in_gitignore.txt")
        with open("test_dir/ignored_in_gitignore.txt", "w") as f:
            f.write("This file should be ignored by .gitignore")
        with open("test_dir/.hidden_ignored_in_gitignore.txt", "w") as f:
            f.write("This hidden file should be ignored by .gitignore")
        with open("test_dir/included.txt", "w") as f:
            f.write("This file should be included")
        with open("test_dir/.hidden_included.txt", "w") as f:
            f.write("This hidden file should be included")
        with open("single_file.txt", "w") as f:
            f.write("Contents of single file")

        result = runner.invoke(cli, ["test_dir", "single_file.txt"])
        assert result.exit_code == 0
        assert "test_dir/ignored_in_gitignore.txt" not in result.output
        assert "test_dir/.hidden_ignored_in_gitignore.txt" not in result.output
        assert "test_dir/included.txt" in result.output
        assert "test_dir/.hidden_included.txt" not in result.output
        assert "single_file.txt" in result.output
        assert "Contents of single file" in result.output

        result = runner.invoke(cli, ["test_dir", "single_file.txt", "--include-hidden"])
        assert result.exit_code == 0
        assert "test_dir/ignored_in_gitignore.txt" not in result.output
        assert "test_dir/.hidden_ignored_in_gitignore.txt" not in result.output
        assert "test_dir/included.txt" in result.output
        assert "test_dir/.hidden_included.txt" in result.output
        assert "single_file.txt" in result.output
        assert "Contents of single file" in result.output

        result = runner.invoke(
            cli, ["test_dir", "single_file.txt", "--ignore-gitignore"]
        )
        assert result.exit_code == 0
        assert "test_dir/ignored_in_gitignore.txt" in result.output
        assert "test_dir/.hidden_ignored_in_gitignore.txt" not in result.output
        assert "test_dir/included.txt" in result.output
        assert "test_dir/.hidden_included.txt" not in result.output
        assert "single_file.txt" in result.output
        assert "Contents of single file" in result.output

        result = runner.invoke(
            cli,
            ["test_dir", "single_file.txt", "--ignore-gitignore", "--include-hidden"],
        )
        assert result.exit_code == 0
        assert "test_dir/ignored_in_gitignore.txt" in result.output
        assert "test_dir/.hidden_ignored_in_gitignore.txt" in result.output
        assert "test_dir/included.txt" in result.output
        assert "test_dir/.hidden_included.txt" in result.output
        assert "single_file.txt" in result.output
        assert "Contents of single file" in result.output


def test_binary_file_warning(tmpdir):
    runner = CliRunner(mix_stderr=False)
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/binary_file.bin", "wb") as f:
            f.write(b"\xff")
        with open("test_dir/text_file.txt", "w") as f:
            f.write("This is a text file")

        result = runner.invoke(cli, ["test_dir"], catch_exceptions=False)
        assert result.exit_code == 0

        stdout = result.stdout
        stderr = result.stderr

        assert "test_dir/text_file.txt" in stdout
        assert "This is a text file" in stdout
        assert "\ntest_dir/binary_file.bin" not in stdout
        assert (
            "Warning: Skipping file test_dir/binary_file.bin due to UnicodeDecodeError"
            in stderr
        )


@pytest.mark.parametrize(
    "args", (["test_dir"], ["test_dir/file1.txt", "test_dir/file2.txt"])
)
def test_xml_format_dir(tmpdir, args):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1.txt")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Contents of file2.txt")
        result = runner.invoke(cli, args + ["--cxml"])
        assert result.exit_code == 0
        actual = result.output
        expected = """
<documents>
<document index="1">
<source>test_dir/file1.txt</source>
<document_content>
Contents of file1.txt
</document_content>
</document>
<document index="2">
<source>test_dir/file2.txt</source>
<document_content>
Contents of file2.txt
</document_content>
</document>
</documents>
"""
        assert expected.strip() == actual.strip()


@pytest.mark.parametrize("arg", ("-o", "--output"))
def test_output_option(tmpdir, arg):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1.txt")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Contents of file2.txt")
        output_file = "output.txt"
        result = runner.invoke(
            cli, ["test_dir", arg, output_file], catch_exceptions=False
        )
        assert result.exit_code == 0
        assert not result.output
        with open(output_file, "r") as f:
            actual = f.read()
        expected = """
test_dir/file1.txt
---
Contents of file1.txt

---
test_dir/file2.txt
---
Contents of file2.txt

---
"""
        assert expected.strip() == actual.strip()


def test_line_numbers(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        test_content = "First line\nSecond line\nThird line\nFourth line\n"
        with open("test_dir/multiline.txt", "w") as f:
            f.write(test_content)

        result = runner.invoke(cli, ["test_dir"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "1  First line" not in result.output
        assert test_content in result.output

        result = runner.invoke(cli, ["test_dir", "-n"])
        assert result.exit_code == 0
        assert "1  First line" in result.output
        assert "2  Second line" in result.output
        assert "3  Third line" in result.output
        assert "4  Fourth line" in result.output

        result = runner.invoke(cli, ["test_dir", "--line-numbers"])
        assert result.exit_code == 0
        assert "1  First line" in result.output
        assert "2  Second line" in result.output
        assert "3  Third line" in result.output
        assert "4  Fourth line" in result.output


@pytest.mark.parametrize(
    "input,extra_args",
    (
        ("test_dir1/file1.txt\ntest_dir2/file2.txt", []),
        ("test_dir1/file1.txt\ntest_dir2/file2.txt", []),
        ("test_dir1/file1.txt\0test_dir2/file2.txt", ["--null"]),
        ("test_dir1/file1.txt\0test_dir2/file2.txt", ["-0"]),
    ),
)
def test_reading_paths_from_stdin(tmpdir, input, extra_args):
    runner = CliRunner()
    with tmpdir.as_cwd():
        # Create test files
        os.makedirs("test_dir1")
        os.makedirs("test_dir2")
        with open("test_dir1/file1.txt", "w") as f:
            f.write("Contents of file1")
        with open("test_dir2/file2.txt", "w") as f:
            f.write("Contents of file2")

        # Test space-separated paths from stdin
        result = runner.invoke(cli, args=extra_args, input=input)
        assert result.exit_code == 0
        assert "test_dir1/file1.txt" in result.output
        assert "Contents of file1" in result.output
        assert "test_dir2/file2.txt" in result.output
        assert "Contents of file2" in result.output


def test_paths_from_arguments_and_stdin(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        # Create test files
        os.makedirs("test_dir1")
        os.makedirs("test_dir2")
        with open("test_dir1/file1.txt", "w") as f:
            f.write("Contents of file1")
        with open("test_dir2/file2.txt", "w") as f:
            f.write("Contents of file2")

        # Test paths from arguments and stdin
        result = runner.invoke(
            cli,
            args=["test_dir1"],
            input="test_dir2/file2.txt",
        )
        assert result.exit_code == 0
        assert "test_dir1/file1.txt" in result.output
        assert "Contents of file1" in result.output
        assert "test_dir2/file2.txt" in result.output
        assert "Contents of file2" in result.output


@pytest.mark.parametrize("option", ("-m", "--markdown"))
def test_markdown(tmpdir, option):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/python.py", "w") as f:
            f.write("This is python")
        with open("test_dir/python_with_quad_backticks.py", "w") as f:
            f.write("This is python with ```` in it already")
        with open("test_dir/code.js", "w") as f:
            f.write("This is javascript")
        with open("test_dir/code.unknown", "w") as f:
            f.write("This is an unknown file type")
        result = runner.invoke(cli, ["test_dir", option])
        assert result.exit_code == 0
        actual = result.output
        expected = (
            "test_dir/code.js\n"
            "```javascript\n"
            "This is javascript\n"
            "```\n"
            "test_dir/code.unknown\n"
            "```\n"
            "This is an unknown file type\n"
            "```\n"
            "test_dir/python.py\n"
            "```python\n"
            "This is python\n"
            "```\n"
            "test_dir/python_with_quad_backticks.py\n"
            "`````python\n"
            "This is python with ```` in it already\n"
            "`````\n"
        )
        assert expected.strip() == actual.strip()
