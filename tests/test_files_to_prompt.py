import os
import pytest
import re
from pathlib import Path
from unittest.mock import patch, MagicMock

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

        output = result.output.replace("\\", "/")

        assert "test_dir/text_file.txt" in output
        assert "This is a text file" in output
        assert "\ntest_dir/binary_file.bin" not in output
        assert (
            "Warning: Skipping file test_dir/binary_file.bin due to UnicodeDecodeError"
            in output
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


@pytest.mark.parametrize("option", ("-C", "--copy"))
def test_copy_to_clipboard(tmpdir, option):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Contents of file2")
        
        # Test successful copy
        with patch('pyperclip.copy') as mock_copy:
            result = runner.invoke(cli, ["test_dir", option])
            assert result.exit_code == 0
            assert "Output copied to clipboard" in result.output
            
            # Verify pyperclip.copy was called with the correct content
            mock_copy.assert_called_once()
            copied_content = mock_copy.call_args[0][0]
            assert "test_dir/file1.txt" in copied_content
            assert "Contents of file1" in copied_content
            assert "test_dir/file2.txt" in copied_content
            assert "Contents of file2" in copied_content


def test_copy_to_clipboard_with_formats(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file.py", "w") as f:
            f.write("print('hello')")
        
        # Test with markdown format
        with patch('pyperclip.copy') as mock_copy:
            result = runner.invoke(cli, ["test_dir", "-C", "--markdown"])
            assert result.exit_code == 0
            assert "Output copied to clipboard" in result.output
            
            copied_content = mock_copy.call_args[0][0]
            assert "```python" in copied_content
            assert "print('hello')" in copied_content
            assert "```" in copied_content
        
        # Test with XML format
        with patch('pyperclip.copy') as mock_copy:
            result = runner.invoke(cli, ["test_dir", "-C", "--cxml"])
            assert result.exit_code == 0
            assert "Output copied to clipboard" in result.output
            
            copied_content = mock_copy.call_args[0][0]
            assert "<documents>" in copied_content
            assert "<document index=" in copied_content
            assert "<source>test_dir/file.py</source>" in copied_content
            assert "</documents>" in copied_content


def test_copy_to_clipboard_failure(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file.txt", "w") as f:
            f.write("Test content")
        
        # Test clipboard failure
        with patch('pyperclip.copy') as mock_copy:
            mock_copy.side_effect = Exception("Clipboard not available")
            result = runner.invoke(cli, ["test_dir", "-C"])
            assert result.exit_code == 0
            assert "Failed to copy to clipboard: Clipboard not available" in result.output
            assert "Output follows:" in result.output
            # When clipboard fails, content should be printed to stdout
            assert "test_dir/file.txt" in result.output
            assert "Test content" in result.output


def test_copy_and_output_conflict(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file.txt", "w") as f:
            f.write("Test content")
        
        # Test that -C and -o together produce an error
        result = runner.invoke(cli, ["test_dir", "-C", "-o", "output.txt"])
        assert result.exit_code == 0
        combined = result.output
        assert "Note: -o/--output overrides -C/--copy" in combined
        # Clipboard should not be invoked
        assert "Output copied to clipboard" not in combined


def test_copy_clipboard_basic(tmpdir):
    """Basic clipboard copy succeeds when pyperclip is available"""
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Contents of file2")
        
        # Provide a stub pyperclip if it's not installed
        import types, sys as _sys
        if 'pyperclip' not in _sys.modules:
            stub = types.ModuleType('pyperclip')
            def _copy(_: str):
                pass
            stub.copy = _copy
            _sys.modules['pyperclip'] = stub

        with patch('pyperclip.copy') as mock_copy:
            # Simulate successful copy on all platforms
            result = runner.invoke(cli, ["test_dir", "-C"])
            assert result.exit_code == 0
            assert "Output copied to clipboard" in result.output
            mock_copy.assert_called_once()
            
            # The actual platform-specific handling is done by pyperclip
            # We just ensure our code calls it correctly


def test_config_file_loading(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.py", "w") as f:
            f.write("Python file")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Text file")
        with open("test_dir/ignored.pyc", "w") as f:
            f.write("Compiled file")
        
        # Create a project config file
        with open(".files-to-prompt.toml", "w") as f:
            f.write("""
[defaults]
extensions = ["py"]
ignore = ["*.pyc"]
line_numbers = true
""")
        
        # Test that config is loaded
        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "test_dir/file1.py" in result.output
        assert "Python file" in result.output
        assert "test_dir/file2.txt" not in result.output  # Only .py files
        assert "test_dir/ignored.pyc" not in result.output  # Ignored
        assert "1  Python file" in result.output  # Line numbers enabled
        
        # Test --no-config flag
        result = runner.invoke(cli, ["test_dir", "--no-config"])
        assert result.exit_code == 0
        assert "test_dir/file1.py" in result.output
        assert "test_dir/file2.txt" in result.output  # All files included
        assert "test_dir/ignored.pyc" in result.output  # Not ignored
        assert "1  Python file" not in result.output  # No line numbers


def test_config_precedence(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.py", "w") as f:
            f.write("Python file")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Text file")
        
        # Create a project config file
        with open(".files-to-prompt.toml", "w") as f:
            f.write("""
[defaults]
extensions = ["py"]
markdown = true
""")
        
        # CLI args should override config
        result = runner.invoke(cli, ["test_dir", "-e", "txt"])
        assert result.exit_code == 0
        assert "test_dir/file1.py" not in result.output
        assert "test_dir/file2.txt" in result.output
        assert "```" in result.output  # Markdown from config
        
        # CLI flag overrides config
        result = runner.invoke(cli, ["test_dir", "--cxml"])
        assert result.exit_code == 0
        assert "<documents>" in result.output  # XML format overrides markdown


def test_config_ignore_patterns_merge(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.py", "w") as f:
            f.write("Python file")
        with open("test_dir/test.pyc", "w") as f:
            f.write("Compiled file")
        with open("test_dir/cache.tmp", "w") as f:
            f.write("Temp file")
        
        # Create a project config file
        with open(".files-to-prompt.toml", "w") as f:
            f.write("""
[defaults]
ignore = ["*.pyc"]
""")
        
        # Config and CLI ignore patterns should merge
        result = runner.invoke(cli, ["test_dir", "--ignore", "*.tmp"])
        assert result.exit_code == 0
        assert "test_dir/file1.py" in result.output
        assert "test_dir/test.pyc" not in result.output  # From config
        assert "test_dir/cache.tmp" not in result.output  # From CLI


def test_config_in_parent_directory(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("nested/deep/test_dir")
        
        # Create config in parent directory
        with open(".files-to-prompt.toml", "w") as f:
            f.write("""
[defaults]
line_numbers = true
""")
        
        with open("nested/deep/test_dir/file.txt", "w") as f:
            f.write("Test content")
        
        # Change to nested directory
        os.chdir("nested/deep")
        
        # Config should still be found
        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "1  Test content" in result.output


def test_user_config(tmpdir, monkeypatch):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file.txt", "w") as f:
            f.write("Test file")
        
        # Create a fake home directory
        fake_home = tmpdir.mkdir("home")
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        
        # Create user config
        config_dir = fake_home.mkdir(".config").mkdir("files-to-prompt")
        with open(config_dir / "config.toml", "w") as f:
            f.write("""
[defaults]
markdown = true
""")
        
        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "```" in result.output  # Markdown from user config


def test_invalid_config_file(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file.txt", "w") as f:
            f.write("Test file")
        
        # Create invalid TOML
        with open(".files-to-prompt.toml", "w") as f:
            f.write("invalid toml {{{")
        
        # Should show warning but continue
        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "Warning: Failed to load config" in result.output
        assert "test_dir/file.txt" in result.output


def test_config_with_output_option(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file.txt", "w") as f:
            f.write("Test file")
        
        # Create config with output option
        with open(".files-to-prompt.toml", "w") as f:
            f.write("""
[defaults]
output = "output.txt"
""")
        
        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert not result.output  # No stdout
        
        # Check output file
        with open("output.txt", "r") as f:
            content = f.read()
        assert "test_dir/file.txt" in content
        assert "Test file" in content


def test_config_boolean_flags(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/.hidden.txt", "w") as f:
            f.write("Hidden file")
        with open("test_dir/normal.txt", "w") as f:
            f.write("Normal file")
        
        # Create config with boolean flags
        with open(".files-to-prompt.toml", "w") as f:
            f.write("""
[defaults]
include_hidden = true
cxml = true
""")
        
        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "test_dir/.hidden.txt" in result.output
        assert "<documents>" in result.output  # XML format
