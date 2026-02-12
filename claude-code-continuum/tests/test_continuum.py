import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import shutil

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'container-files'))

from continuum import ContinuumRepo

@pytest.fixture
def temp_continuum():
    """Create temporary continuum directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

def test_init_creates_directory_structure(temp_continuum):
    """Test that init creates expected directory structure"""
    repo = ContinuumRepo(str(temp_continuum))
    repo.init()

    assert (temp_continuum / 'sessions').exists()
    assert (temp_continuum / 'knowledge').exists()
    assert (temp_continuum / 'config').exists()
    assert (temp_continuum / 'config' / 'blocklist.txt').exists()
    assert (temp_continuum / 'config' / 'auto-load-rules.yaml').exists()

def test_init_creates_default_blocklist(temp_continuum):
    """Test that init creates blocklist with expected commands"""
    repo = ContinuumRepo(str(temp_continuum))
    repo.init()

    blocklist_file = temp_continuum / 'config' / 'blocklist.txt'
    content = blocklist_file.read_text()

    assert 'rm -rf' in content
    assert 'sudo' in content
    assert 'chmod' in content
    assert 'dd' in content

def test_list_sessions_empty(temp_continuum):
    """Test listing sessions when none exist"""
    repo = ContinuumRepo(str(temp_continuum))
    repo.init()

    sessions = repo.list_sessions()
    assert sessions == []
