import os

from click.testing import CliRunner

from files_to_prompt.cli import cli


def test_symlink_pointing_outside_the_tree_is_not_followed(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("outside")
        with open("outside/secret.txt", "w") as f:
            f.write("SECRET_FROM_OUTSIDE_THE_TREE")
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1")
        os.symlink(os.path.abspath("outside/secret.txt"), "test_dir/innocent.txt")

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "Contents of file1" in result.output
        assert "SECRET_FROM_OUTSIDE_THE_TREE" not in result.output


def test_symlink_pointing_inside_the_tree_is_still_followed(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir/docs")
        with open("test_dir/docs/real.md", "w") as f:
            f.write("Contents of real")
        os.symlink(os.path.join("docs", "real.md"), "test_dir/alias.md")

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "test_dir/docs/real.md" in result.output
        assert "test_dir/alias.md" in result.output
        assert result.output.count("Contents of real") == 2


def test_broken_symlink_does_not_discard_the_rest_of_the_run(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/a.txt", "w") as f:
            f.write("Contents of a")
        os.symlink("nowhere.txt", "test_dir/m_broken.txt")
        with open("test_dir/z.txt", "w") as f:
            f.write("Contents of z")

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "Contents of a" in result.output
        assert "Contents of z" in result.output
