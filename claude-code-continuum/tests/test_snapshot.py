import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from pathlib import Path
import json

# Add container-files to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'container-files'))

from continuum import ContinuumRepo

def test_create_snapshot_generates_session_id(tmp_path):
    """Test that create_snapshot generates a valid session ID"""
    workspace = tmp_path / 'workspace'
    workspace.mkdir()

    continuum_path = tmp_path / '.continuum'
    repo = ContinuumRepo(str(continuum_path))
    repo.init()

    with patch('subprocess.run') as mock_run:
        # Mock hostname and uname
        mock_run.side_effect = [
            MagicMock(stdout='test-host', returncode=0),  # hostname
            MagicMock(stdout='5.15.0-test', returncode=0),  # uname -r
            MagicMock(returncode=1),  # git rev-parse (not a repo)
        ]

        with patch('shutil.copy'):  # Mock conversation copy
            metadata = repo.create_snapshot(workspace, "Test session")

    assert 'session_id' in metadata
    assert metadata['session_id'].startswith('session-')
    assert len(metadata['session_id'].split('-')) == 4  # session-YYYYMMDD-HHMMSS-uuid

def test_snapshot_captures_host_details(tmp_path):
    """Test that snapshot captures hostname and kernel version"""
    workspace = tmp_path / 'workspace'
    workspace.mkdir()

    continuum_path = tmp_path / '.continuum'
    repo = ContinuumRepo(str(continuum_path))
    repo.init()

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout='my-laptop', returncode=0),  # hostname
            MagicMock(stdout='6.1.0-17-amd64', returncode=0),  # uname -r
            MagicMock(returncode=1),  # git rev-parse
        ]

        with patch('shutil.copy'):
            metadata = repo.create_snapshot(workspace, "Test")

    assert metadata['hostname'] == 'my-laptop'
    assert metadata['kernel_version'] == '6.1.0-17-amd64'

def test_snapshot_saves_metadata_file(tmp_path):
    """Test that snapshot creates metadata.json file"""
    workspace = tmp_path / 'workspace'
    workspace.mkdir()

    continuum_path = tmp_path / '.continuum'
    repo = ContinuumRepo(str(continuum_path))
    repo.init()

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout='test-host', returncode=0),
            MagicMock(stdout='5.15.0-test', returncode=0),
            MagicMock(returncode=1),  # not a git repo
        ]

        with patch('shutil.copy'):
            metadata = repo.create_snapshot(workspace, "Test session")

    session_id = metadata['session_id']
    metadata_file = continuum_path / 'sessions' / session_id / 'metadata.json'

    assert metadata_file.exists()

    with open(metadata_file) as f:
        saved_metadata = json.load(f)

    assert saved_metadata['session_id'] == session_id
    assert saved_metadata['description'] == "Test session"
    assert saved_metadata['workspace_path'] == str(workspace.absolute())

def test_snapshot_captures_git_branch(tmp_path):
    """Test that snapshot captures current git branch"""
    workspace = tmp_path / 'workspace'
    workspace.mkdir()

    continuum_path = tmp_path / '.continuum'
    repo = ContinuumRepo(str(continuum_path))
    repo.init()

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout='test-host', returncode=0),  # hostname
            MagicMock(stdout='5.15.0-test', returncode=0),  # uname -r
            MagicMock(returncode=0),  # git rev-parse (is a repo)
            MagicMock(stdout='feature/my-branch', returncode=0),  # git branch
            MagicMock(stdout='', returncode=0),  # git status (no changes)
            MagicMock(returncode=1),  # git log (no unpushed)
        ]

        with patch('shutil.copy'):
            metadata = repo.create_snapshot(workspace)

    assert metadata['git']['is_repo'] is True
    assert metadata['git']['branch'] == 'feature/my-branch'
    assert metadata['git']['has_uncommitted'] is False

def test_snapshot_detects_uncommitted_changes(tmp_path):
    """Test that snapshot detects uncommitted changes"""
    workspace = tmp_path / 'workspace'
    workspace.mkdir()

    continuum_path = tmp_path / '.continuum'
    repo = ContinuumRepo(str(continuum_path))
    repo.init()

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout='test-host', returncode=0),
            MagicMock(stdout='5.15.0-test', returncode=0),
            MagicMock(returncode=0),  # is a git repo
            MagicMock(stdout='main', returncode=0),  # git branch
            MagicMock(stdout=' M file.txt\n', returncode=0),  # git status (has changes)
            MagicMock(returncode=1),  # git log (no unpushed)
            MagicMock(stdout='diff content', returncode=0),  # git diff
        ]

        with patch('shutil.copy'):
            metadata = repo.create_snapshot(workspace)

    assert metadata['git']['has_uncommitted'] is True

    # Check that snapshot.patch was created
    session_id = metadata['session_id']
    patch_file = continuum_path / 'sessions' / session_id / 'snapshot.patch'
    assert patch_file.exists()

def test_commit_and_push_snapshot_success(tmp_path):
    """Test that commit_and_push_snapshot commits and pushes"""
    continuum_path = tmp_path / '.continuum'
    repo = ContinuumRepo(str(continuum_path))
    repo.init()

    # Create a fake session directory
    session_id = 'session-20260217-120000-abcd1234'
    session_dir = continuum_path / 'sessions' / session_id
    session_dir.mkdir(parents=True)
    (session_dir / 'metadata.json').write_text('{}')

    with patch('subprocess.run') as mock_run:
        # git add, git diff (has changes), git commit, git push
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=1),  # git diff --cached --quiet (has changes)
            MagicMock(returncode=0),  # git commit
            MagicMock(returncode=0),  # git push
        ]

        result = repo.commit_and_push_snapshot(session_id, "Test snapshot")

    assert result is True

def test_commit_and_push_handles_no_changes(tmp_path):
    """Test that commit_and_push_snapshot handles case with no changes"""
    continuum_path = tmp_path / '.continuum'
    repo = ContinuumRepo(str(continuum_path))
    repo.init()

    session_id = 'session-20260217-120000-abcd1234'

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=0),  # git diff --cached --quiet (no changes)
        ]

        result = repo.commit_and_push_snapshot(session_id, "Test")

    assert result is True
    # Should not have attempted commit or push (only 2 calls: add and diff)
    assert mock_run.call_count == 2
