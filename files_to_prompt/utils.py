from pathlib import Path
from pathspec.gitignore import GitIgnoreSpec


def allowed_by_gitignore(root: Path, file_path: Path) -> bool:
    """
    Check whether the file (file_path) should be included (i.e. not ignored)
    based on all .gitignore files encountered from the root directory down to
    the directory where the file resides.

    Parameters:
      root (Path): The root directory under which .gitignore files are searched.
      file_path (Path): The file to be checked.

    Returns:
      bool: True if the file should be included (not ignored); False if it should be ignored.
    """
    # Resolve absolute paths.
    abs_root = root.resolve()
    abs_file = file_path.resolve()

    # Ensure file is under the provided root.
    try:
        _ = abs_file.relative_to(abs_root)
    except ValueError:
        raise ValueError(f"File {abs_file!r} is not under the root {abs_root!r}.")

    # Build a list of directories from the root to the file's directory.
    directories = [abs_root]
    file_dir = abs_file.parent
    rel_dir = file_dir.relative_to(abs_root)
    for part in rel_dir.parts:
        directories.append(directories[-1] / part)

    # The decision will be updated by any matching .gitignore rule encountered.
    decision = None

    # Process each directory (from root to file's directory)
    for directory in directories:
        gitignore_file = directory / ".gitignore"
        if gitignore_file.is_file():
            try:
                # Read nonempty lines (ignoring blank lines).
                lines = [
                    line.rstrip("\n")
                    for line in gitignore_file.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            except Exception as e:
                print(f"Could not read {gitignore_file}: {e}")
                continue

            # Compile a GitIgnoreSpec for the rules in the current directory.
            spec = GitIgnoreSpec.from_lines(lines)

            # .gitignore patterns are relative to the directory they are in.
            # Compute the file path relative to this directory in POSIX format.
            rel_file = abs_file.relative_to(directory).as_posix()

            # Check the file against these rules.
            result = spec.check_file(rel_file)

            # If a rule from this .gitignore file applied, update the decision.
            if result.include is not None:
                decision = result.include

    # If no .gitignore rule matched, the file is included by default.
    if decision is None:
        return True

    # Interpretation:
    #   • decision == True  --> a normal ignore rule matched (file should be ignored)
    #   • decision == False --> a negation rule matched (file re-included)
    # So, we return not decision.
    return not decision
