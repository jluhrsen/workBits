import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# Add container-files to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'container-files'))

from session_manager import SessionManager

def test_banner_shows_workspace_path():
    """Test that banner displays current workspace path"""
    with patch.dict(os.environ, {'CONTINUUM_REPO_URL': ''}):
        manager = SessionManager()
        banner = manager.generate_banner('/workspace/test-repo')

        assert '/workspace/test-repo' in banner
        assert 'READ/WRITE ACCESS' in banner

def test_banner_shows_continuum_repo_when_set():
    """Test that banner shows continuum repo URL when configured"""
    test_url = 'git@github.com:test/continuum.git'
    with patch.dict(os.environ, {'CONTINUUM_REPO_URL': test_url}):
        manager = SessionManager()
        banner = manager.generate_banner('/workspace')

        assert test_url in banner

def test_banner_shows_local_mode_when_no_repo():
    """Test that banner shows local-only mode when no repo configured"""
    with patch.dict(os.environ, {'CONTINUUM_REPO_URL': ''}):
        manager = SessionManager()
        banner = manager.generate_banner('/workspace')

        assert 'local only' in banner.lower() or 'CONTINUUM_REPO_URL not set' in banner

def test_sync_continuum_when_url_set(tmp_path):
    """Test that session manager syncs continuum when URL is configured"""
    continuum_dir = tmp_path / '.continuum'

    with patch.dict(os.environ, {
        'CONTINUUM_REPO_URL': 'git@github.com:test/continuum.git',
        'HOME': str(tmp_path)
    }):
        with patch('session_manager.ContinuumRepo') as mock_repo:
            manager = SessionManager()
            manager.sync_continuum()

            # Should have attempted to clone or pull
            mock_repo.return_value.clone_or_pull.assert_called_once()

def test_no_sync_when_url_not_set(tmp_path):
    """Test that session manager skips sync when no URL configured"""
    with patch.dict(os.environ, {'CONTINUUM_REPO_URL': '', 'HOME': str(tmp_path)}):
        with patch('session_manager.ContinuumRepo') as mock_repo:
            manager = SessionManager()
            manager.sync_continuum()

            # Should not attempt sync
            mock_repo.return_value.clone_or_pull.assert_not_called()
