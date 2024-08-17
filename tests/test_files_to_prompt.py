import os
import base64
import xml.etree.ElementTree as ET
from click.testing import CliRunner
from files_to_prompt.cli import cli


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
        with open("test_dir/.gitignore", "w") as f:
            f.write("ignored.txt")
        with open("test_dir/ignored.txt", "w") as f:
            f.write("This file should be ignored")
        with open("test_dir/included.txt", "w") as f:
            f.write("This file should be included")

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "test_dir/ignored.txt" not in result.output
        assert "test_dir/included.txt" in result.output

        result = runner.invoke(cli, ["test_dir", "--ignore-gitignore"])
        assert result.exit_code == 0
        assert "test_dir/ignored.txt" in result.output
        assert "This file should be ignored" in result.output
        assert "test_dir/included.txt" in result.output


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
        os.makedirs("test_dir")
        with open("test_dir/file_to_ignore.txt", "w") as f:
            f.write("This file should be ignored due to ignore patterns")
        with open("test_dir/file_to_include.txt", "w") as f:
            f.write("This file should be included")

        result = runner.invoke(cli, ["test_dir", "--ignore", "*.txt"])
        assert result.exit_code == 0
        assert "test_dir/file_to_ignore.txt" not in result.output
        assert "This file should be ignored due to ignore patterns" not in result.output
        assert "test_dir/file_to_include.txt" not in result.output

        result = runner.invoke(cli, ["test_dir", "--ignore", "file_to_ignore.*"])
        assert result.exit_code == 0
        assert "test_dir/file_to_ignore.txt" not in result.output
        assert "This file should be ignored due to ignore patterns" not in result.output
        assert "test_dir/file_to_include.txt" in result.output
        assert "This file should be included" in result.output


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


def test_claude_xml_output(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Contents of file2")

        result = runner.invoke(cli, ["test_dir", "--format", "claude-xml"])
        assert result.exit_code == 0

        # Parse the XML output
        root = ET.fromstring(result.output)

        # Check the structure of the XML
        assert root.tag == "documents"
        documents = root.findall("document")

        # Print out all sources for debugging
        sources = [doc.find("source").text for doc in documents]
        print(f"Found sources: {sources}")

        # Check if the expected files are in the output
        expected_files = ["test_dir/file1.txt", "test_dir/file2.txt"]
        for expected_file in expected_files:
            assert any(
                doc.find("source").text == expected_file for doc in documents
            ), f"Expected file {expected_file} not found in output"

        for doc in documents:
            assert "index" in doc.attrib
            assert doc.find("source") is not None
            assert doc.find("document_content") is not None

            source = doc.find("source").text
            content = doc.find("document_content").text

            if source in expected_files:
                assert content in ["Contents of file1", "Contents of file2"]


def test_claude_xml_b64_output(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1")
        with open("test_dir/binary_file.bin", "wb") as f:
            f.write(b"\xff\x00\xff")

        result = runner.invoke(cli, ["test_dir", "--format", "claude-xml-b64"])
        assert result.exit_code == 0

        # Parse the XML output
        root = ET.fromstring(result.output)

        # Check the structure of the XML
        assert root.tag == "documents"
        documents = root.findall("document")

        # Print out all sources for debugging
        sources = [doc.find("source").text for doc in documents]
        print(f"Found sources: {sources}")

        # Check if the expected files are in the output
        expected_files = ["test_dir/file1.txt", "test_dir/binary_file.bin"]
        for expected_file in expected_files:
            assert any(
                doc.find("source").text == expected_file for doc in documents
            ), f"Expected file {expected_file} not found in output"

        # Check for no duplication
        assert len(documents) == len(
            expected_files
        ), f"Expected {len(expected_files)} documents, but found {len(documents)}"

        for doc in documents:
            assert "index" in doc.attrib
            assert doc.find("source") is not None
            assert doc.find("document_content") is not None

            source = doc.find("source").text
            content = doc.find("document_content").text

            if source == "test_dir/file1.txt":
                # Text file should not be base64 encoded
                assert content == "Contents of file1"
            elif source == "test_dir/binary_file.bin":
                # Binary file should be base64 encoded
                decoded = base64.b64decode(content)
                assert decoded == b"\xff\x00\xff"


def test_no_duplication_in_output(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Contents of file2")
        with open("test_dir/binary_file.bin", "wb") as f:
            f.write(b"\xff\x00\xff")

        for format in ["claude-xml", "claude-xml-b64"]:
            result = runner.invoke(cli, ["test_dir", "--format", format])
            assert result.exit_code == 0

            # Split the output into warnings and XML content
            output_lines = result.output.split("\n")
            warnings = [line for line in output_lines if line.startswith("Warning:")]
            xml_content = "\n".join(
                [line for line in output_lines if not line.startswith("Warning:")]
            )

            print(f"Warnings for {format}:")
            for warning in warnings:
                print(warning)

            print(f"\nXML content for {format}:")
            print(xml_content)

            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError as e:
                print(f"XML parsing error for {format}: {e}")
                print("Full output:")
                print(result.output)
                raise

            documents = root.findall("document")
            sources = [doc.find("source").text for doc in documents]

            print(f"\nFound sources for {format}: {sources}")

            # Check for no duplication
            assert len(documents) == len(
                set(sources)
            ), f"Duplication found in {format} output: {sources}"

            # Expected count differs based on format
            if format == "claude-xml":
                expected_count = (
                    2  # file1.txt and file2.txt (binary_file.bin is skipped)
                )
            else:  # claude-xml-b64
                expected_count = 3  # file1.txt, file2.txt, and binary_file.bin

            assert (
                len(documents) == expected_count
            ), f"Expected {expected_count} documents, but found {len(documents)} in {format} output"

            # Additional checks for claude-xml-b64
            if format == "claude-xml-b64":
                binary_doc = next(
                    (
                        doc
                        for doc in documents
                        if doc.find("source").text == "test_dir/binary_file.bin"
                    ),
                    None,
                )
                assert (
                    binary_doc is not None
                ), "Binary file not found in claude-xml-b64 output"
                binary_content = binary_doc.find("document_content").text
                assert (
                    base64.b64decode(binary_content) == b"\xff\x00\xff"
                ), "Binary content doesn't match expected value"


def test_claude_xml_with_hidden_and_gitignore(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/.gitignore", "w") as f:
            f.write("ignored.txt")
        with open("test_dir/ignored.txt", "w") as f:
            f.write("This file should be ignored")
        with open("test_dir/.hidden.txt", "w") as f:
            f.write("This is a hidden file")
        with open("test_dir/normal.txt", "w") as f:
            f.write("This is a normal file")

        # Test claude-xml format
        result = runner.invoke(cli, ["test_dir", "--format", "claude-xml"])
        assert result.exit_code == 0
        root = ET.fromstring(result.output)
        sources = [doc.find("source").text for doc in root.findall("document")]
        assert "test_dir/normal.txt" in sources
        assert "test_dir/ignored.txt" not in sources
        assert "test_dir/.hidden.txt" not in sources

        # Test with --include-hidden
        result = runner.invoke(
            cli, ["test_dir", "--format", "claude-xml", "--include-hidden"]
        )
        assert result.exit_code == 0
        root = ET.fromstring(result.output)
        sources = [doc.find("source").text for doc in root.findall("document")]
        assert "test_dir/normal.txt" in sources
        assert "test_dir/ignored.txt" not in sources
        assert "test_dir/.hidden.txt" in sources

        # Test with --ignore-gitignore
        result = runner.invoke(
            cli, ["test_dir", "--format", "claude-xml", "--ignore-gitignore"]
        )
        assert result.exit_code == 0
        root = ET.fromstring(result.output)
        sources = [doc.find("source").text for doc in root.findall("document")]
        assert "test_dir/normal.txt" in sources
        assert "test_dir/ignored.txt" in sources
        assert "test_dir/.hidden.txt" not in sources

        # Test with both --include-hidden and --ignore-gitignore
        result = runner.invoke(
            cli,
            [
                "test_dir",
                "--format",
                "claude-xml",
                "--include-hidden",
                "--ignore-gitignore",
            ],
        )
        assert result.exit_code == 0
        root = ET.fromstring(result.output)
        sources = [doc.find("source").text for doc in root.findall("document")]
        assert "test_dir/normal.txt" in sources
        assert "test_dir/ignored.txt" in sources
        assert "test_dir/.hidden.txt" in sources
