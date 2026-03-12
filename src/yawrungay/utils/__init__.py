"""Utility functions for Yawrungay."""

from pathlib import Path


def find_git_root(start: Path) -> Path:
    """Find git repository root by walking up from start directory.

    If no git repository is found, returns the user's home directory.

    Args:
        start: Starting directory path.

    Returns:
        Path to git root, or user's home directory if not in a git repo.
    """
    current = start
    home = Path.home()
    filesystem_root = Path("/")

    while current != current.parent and current != home and current != filesystem_root:
        if (current / ".git").is_dir():
            return current
        current = current.parent

    # Check final directory (home or filesystem root)
    if (current / ".git").is_dir():
        return current

    return home


def find_project_dirs(start: Path, dirname: str) -> list[Path]:
    """Find project directories by searching for a subdirectory.

    Searches from current working directory upward through parent
    directories, stopping at git repository root or user's home.

    Args:
        start: Starting directory path.
        dirname: Name of the directory to find (e.g., '.yawrungay').

    Returns:
        List of paths to found directories, in order from closest to
        start to farthest (so later ones can override).
    """
    git_root = find_git_root(start)
    dirs = []

    current = start
    while current != git_root:
        project_dir = current / dirname
        if project_dir.exists() and project_dir.is_dir():
            dirs.append(project_dir)
        current = current.parent

    # Also check git root itself
    project_dir = git_root / dirname
    if project_dir.exists() and project_dir.is_dir():
        dirs.append(project_dir)

    return dirs
