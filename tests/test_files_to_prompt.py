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

        result = runner.invoke(cli, ["test_dir"])
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

        result = runner.invoke(cli, ["test_dir"])
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
            f.write("nested_ignore.txt")
        with open("test_dir/nested_ignore/nested_ignore.txt", "w") as f:
            f.write("This nested file should not be included")
        with open("test_dir/nested_ignore/actually_include.txt", "w") as f:
            f.write("This nested file should actually be included")

        result = runner.invoke(cli, ["test_dir", "-c"])
        assert result.exit_code == 0
        filenames = filenames_from_cxml(result.output)

        assert filenames == {
            "test_dir/included.txt",
            "test_dir/nested_include/included2.txt",
            "test_dir/nested_ignore/actually_include.txt",
        }

        result2 = runner.invoke(cli, ["test_dir", "-c", "--ignore-gitignore"])
        assert result2.exit_code == 0
        filenames2 = filenames_from_cxml(result2.output)

        assert filenames2 == {
            "test_dir/included.txt",
            "test_dir/ignored.txt",
            "test_dir/nested_include/included2.txt",
            "test_dir/nested_ignore/nested_ignore.txt",
            "test_dir/nested_ignore/actually_include.txt",
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

        result = runner.invoke(cli, ["test_dir"])
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

        result = runner.invoke(cli, ["test_dir"])
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


def test_stats_basic(tmpdir):
    runner = CliRunner(mix_stderr=False)
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.py", "w") as f:
            f.write("def hello():\n    return 'world'")
        with open("test_dir/file2.py", "w") as f:
            f.write("# A comment\n" * 50)
        
        result = runner.invoke(cli, ["test_dir", "--stats"])
        assert result.exit_code == 0
        
        # Check stdout has normal output
        assert "test_dir/file1.py" in result.stdout
        assert "def hello():" in result.stdout
        
        # Check stderr has stats
        assert "Summary:" in result.stderr
        assert "Files processed: 2" in result.stderr
        assert "Total tokens:" in result.stderr
        assert "Total lines:" in result.stderr
        assert "Top 20 files by token count:" in result.stderr
        assert "test_dir/file1.py" in result.stderr
        assert "test_dir/file2.py" in result.stderr
        assert "Token count by directory:" in result.stderr


def test_stats_with_subdirectories(tmpdir):
    runner = CliRunner(mix_stderr=False)
    with tmpdir.as_cwd():
        os.makedirs("src/models")
        os.makedirs("src/utils")
        os.makedirs("tests")
        
        with open("src/models/user.py", "w") as f:
            f.write("class User:\n    pass\n" * 20)
        with open("src/utils/helpers.py", "w") as f:
            f.write("def helper():\n    pass\n" * 10)
        with open("tests/test_user.py", "w") as f:
            f.write("def test_user():\n    pass\n" * 5)
        with open("README.md", "w") as f:
            f.write("# Project README\n" * 3)
        
        result = runner.invoke(cli, [".", "--stats"])
        assert result.exit_code == 0
        
        # Check directory aggregation
        assert "src" in result.stderr
        assert "tests" in result.stderr
        assert "(root)" in result.stderr  # For README.md
        assert "tokens (" in result.stderr  # Check percentage display


def test_stats_with_ignored_files(tmpdir):
    runner = CliRunner(mix_stderr=False)
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        
        # Create a binary file that will be skipped
        with open("test_dir/binary.bin", "wb") as f:
            f.write(b"\xff\xfe\xfd")
        
        # Create text files
        with open("test_dir/text1.txt", "w") as f:
            f.write("This is text")
        with open("test_dir/text2.txt", "w") as f:
            f.write("More text here")
        
        result = runner.invoke(cli, ["test_dir", "--stats"])
        assert result.exit_code == 0
        
        # Should show ignored files
        assert "Files ignored: 1" in result.stderr
        assert "Files processed: 2" in result.stderr


def test_stats_with_extensions_filter(tmpdir):
    runner = CliRunner(mix_stderr=False)
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        
        with open("test_dir/code.py", "w") as f:
            f.write("print('hello')")
        with open("test_dir/doc.md", "w") as f:
            f.write("# Documentation")
        with open("test_dir/data.json", "w") as f:
            f.write('{"key": "value"}')
        
        result = runner.invoke(cli, ["test_dir", "--stats", "-e", "py", "-e", "md"])
        assert result.exit_code == 0
        
        # Only .py and .md files should be processed
        assert "Files processed: 2" in result.stderr
        assert "test_dir/code.py" in result.stderr
        assert "test_dir/doc.md" in result.stderr
        assert "test_dir/data.json" not in result.stderr


def test_stats_with_output_file(tmpdir):
    runner = CliRunner(mix_stderr=False)
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file.txt", "w") as f:
            f.write("Content")
        
        result = runner.invoke(cli, ["test_dir", "--stats", "-o", "output.txt"])
        assert result.exit_code == 0
        
        # Stats should still go to stderr
        assert "Summary:" in result.stderr
        assert "Files processed: 1" in result.stderr
        
        # Main output should be in file
        with open("output.txt", "r") as f:
            content = f.read()
            assert "test_dir/file.txt" in content
            assert "Content" in content


def test_stats_empty_directory(tmpdir):
    runner = CliRunner(mix_stderr=False)
    with tmpdir.as_cwd():
        os.makedirs("empty_dir")
        
        result = runner.invoke(cli, ["empty_dir", "--stats"])
        assert result.exit_code == 0
        
        assert "Files processed: 0" in result.stderr
        assert "Total tokens: 0" in result.stderr


def test_stats_token_counting_accuracy(tmpdir):
    """Test that token counting is working (tiktoken or fallback)."""
    runner = CliRunner(mix_stderr=False)
    with tmpdir.as_cwd():
        # Create a file with known content
        content = "The quick brown fox jumps over the lazy dog. " * 10
        
        with open("test.txt", "w") as f:
            f.write(content)
        
        result = runner.invoke(cli, ["test.txt", "--stats"])
        assert result.exit_code == 0
        
        # Should show some reasonable token count
        # The exact count depends on whether tiktoken is installed
        assert "Total tokens:" in result.stderr
        # Extract token count from output
        import re
        match = re.search(r"Total tokens: ([\d,]+)", result.stderr)
        assert match
        token_count = int(match.group(1).replace(",", ""))
        # Should be reasonable - not 0, not huge
        assert 50 < token_count < 500  # Reasonable range for repeated sentence
