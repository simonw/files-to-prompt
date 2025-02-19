from files_to_prompt.utils import allowed_by_gitignore
from pathlib import Path


def test_allowed_by_gitignore(tmpdir):
    # Create a temporary directory structure.
    base = Path(tmpdir)
    repo = base / "repo"
    repo.mkdir()

    # Create a top-level .gitignore in repo that ignores the "build/" directory.
    (repo / ".gitignore").write_text("build/\n", encoding="utf-8")

    # Create a "build" subdirectory and add an output file which should be ignored.
    build_dir = repo / "build"
    build_dir.mkdir()
    output_file = build_dir / "output.txt"
    output_file.write_text("dummy build output", encoding="utf-8")

    # Create a "src" subdirectory with its own .gitignore.
    src_dir = repo / "src"
    src_dir.mkdir()
    # In src, ignore "temp.txt"
    (src_dir / ".gitignore").write_text("temp.txt\n", encoding="utf-8")

    # Create files in "src"
    main_file = src_dir / "main.py"
    main_file.write_text("print('Hello')", encoding="utf-8")
    temp_file = src_dir / "temp.txt"
    temp_file.write_text("should be ignored", encoding="utf-8")
    keep_file = src_dir / "keep.txt"
    keep_file.write_text("keep this file", encoding="utf-8")

    # Create a file at repo root that is not ignored.
    root_file = repo / "README.md"
    root_file.write_text("# Repo README", encoding="utf-8")

    # Test cases:
    # 1. File in "build" should be ignored.
    assert (
        allowed_by_gitignore(repo, output_file) is False
    ), "build/output.txt should be ignored"

    # 2. File in "src" that is ignored per src/.gitignore.
    assert allowed_by_gitignore(repo, temp_file) is False, "src/temp.txt should be ignored"

    # 3. Files in "src" not mentioned in .gitignore should be included.
    assert allowed_by_gitignore(repo, main_file) is True, "src/main.py should be included"
    assert allowed_by_gitignore(repo, keep_file) is True, "src/keep.txt should be included"

    # 4. File at the repo root not mentioned in .gitignore.
    assert (
        allowed_by_gitignore(repo, root_file) is True
    ), "repo/README.md should be included"
