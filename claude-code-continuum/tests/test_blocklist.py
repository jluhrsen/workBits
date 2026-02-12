import pytest
from pathlib import Path
import tempfile
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'container-files'))

from blocklist import CommandBlocklist

@pytest.fixture
def temp_blocklist():
    """Create temporary blocklist file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("rm -rf\n")
        f.write("sudo\n")
        f.write("chmod\n")
        f.write("dd\n")
        f.write("mkfs.*\n")
        temp_path = f.name

    yield temp_path
    os.unlink(temp_path)

def test_exact_match_blocked(temp_blocklist):
    """Test that exact command match is blocked"""
    blocklist = CommandBlocklist(temp_blocklist)

    assert blocklist.is_blocked("sudo apt install vim")
    assert blocklist.is_blocked("rm -rf /tmp/test")
    assert blocklist.is_blocked("chmod 777 file.txt")

def test_pattern_match_blocked(temp_blocklist):
    """Test that regex patterns are matched"""
    blocklist = CommandBlocklist(temp_blocklist)

    assert blocklist.is_blocked("mkfs.ext4 /dev/sda1")
    assert blocklist.is_blocked("mkfs /dev/sda1")

def test_allowed_commands_pass(temp_blocklist):
    """Test that non-blocked commands pass through"""
    blocklist = CommandBlocklist(temp_blocklist)

    assert not blocklist.is_blocked("ls -la")
    assert not blocklist.is_blocked("git status")
    assert not blocklist.is_blocked("make test")

def test_remove_from_blocklist(temp_blocklist):
    """Test removing command from blocklist"""
    blocklist = CommandBlocklist(temp_blocklist)

    assert blocklist.is_blocked("sudo test")
    blocklist.remove_pattern("sudo")
    assert not blocklist.is_blocked("sudo test")
