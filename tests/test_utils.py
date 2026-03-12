"""Tests for yawrungay.utils module."""

import os
import tempfile
from pathlib import Path

import pytest

from yawrungay.utils import find_git_root, find_project_dirs


class TestFindGitRoot:
    """Tests for find_git_root function."""

    def test_finds_git_root_from_nested_directory(self, tmp_path):
        """Test finding git root from a nested subdirectory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)

        result = find_git_root(nested)
        assert result == tmp_path

    def test_finds_git_root_at_cwd(self, tmp_path):
        """Test finding git root when starting from the git root itself."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        result = find_git_root(tmp_path)
        assert result == tmp_path

    def test_returns_home_if_not_in_git_repo(self, tmp_path):
        """Test that it returns home if not in a git repo."""
        # Use tmp_path which has no .git in its parents
        result = find_git_root(tmp_path)
        assert result == Path.home()


class TestFindProjectDirs:
    """Tests for find_project_dirs function."""

    def test_finds_directory_at_cwd(self, tmp_path):
        """Test finding project directory at current working directory."""
        # Create a git marker to stop search
        (tmp_path / ".git").mkdir()

        project_dir = tmp_path / ".yawrungay"
        project_dir.mkdir()

        result = find_project_dirs(tmp_path, ".yawrungay")
        assert result == [project_dir]

    def test_finds_directory_in_parent(self, tmp_path):
        """Test finding project directory in parent directory."""
        # Create a git marker to stop search
        (tmp_path / ".git").mkdir()

        project_dir = tmp_path / ".yawrungay"
        project_dir.mkdir()

        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)

        result = find_project_dirs(nested, ".yawrungay")
        assert result == [project_dir]

    def test_finds_multiple_directories_up_chain(self, tmp_path):
        """Test finding multiple project directories in parent chain."""
        # Create a git marker to stop search
        (tmp_path / ".git").mkdir()

        dir1 = tmp_path / ".yawrungay"
        dir1.mkdir()

        subdir1 = tmp_path / "project1"
        subdir1.mkdir()
        dir2 = subdir1 / ".yawrungay"
        dir2.mkdir()

        nested = subdir1 / "src"
        nested.mkdir(parents=True)

        result = find_project_dirs(nested, ".yawrungay")
        # Results are in order from closest to farthest
        assert result == [dir2, dir1]

    def test_returns_empty_list_when_not_found(self, tmp_path):
        """Test that empty list is returned when directory not found."""
        # Create a git marker to stop search
        (tmp_path / ".git").mkdir()

        result = find_project_dirs(tmp_path, ".yawrungay")
        assert result == []

    def test_finds_directory_at_git_root(self, tmp_path):
        """Test finding project directory at git root."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        project_dir = tmp_path / ".yawrungay"
        project_dir.mkdir()

        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)

        result = find_project_dirs(nested, ".yawrungay")
        assert result == [project_dir]

    def test_excludes_non_directories(self, tmp_path):
        """Test that files with same name are excluded."""
        # Create a git marker to stop search
        (tmp_path / ".git").mkdir()

        project_file = tmp_path / ".yawrungay"
        project_file.touch()

        result = find_project_dirs(tmp_path, ".yawrungay")
        assert result == []
