"""
Tests for the commit module functions.
"""

import pytest
from unittest.mock import patch, Mock
from codelog.commit import (
    get_most_recent_commit_hash,
    get_commit_hash,
    ensure_code_is_tracked,
    _run_git_command,
    _is_working_directory_clean
)


class TestRunGitCommand:
    """Tests for the _run_git_command helper function."""
    
    @patch('subprocess.run')
    def test_successful_git_command(self, mock_run):
        """Test successful git command execution."""
        mock_result = Mock()
        mock_result.stdout = "abc123\n"
        mock_run.return_value = mock_result
        
        result = _run_git_command(['rev-parse', 'HEAD'])
        
        assert result == "abc123"
        mock_run.assert_called_once_with(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('subprocess.run')
    def test_successful_git_command_with_path(self, mock_run):
        """Test successful git command execution with specific path."""
        mock_result = Mock()
        mock_result.stdout = "abc123\n"
        mock_run.return_value = mock_result
        
        result = _run_git_command(['rev-parse', 'HEAD'], '/path/to/repo')
        
        assert result == "abc123"
        mock_run.assert_called_once_with(
            ['git', '-C', '/path/to/repo', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('subprocess.run')
    def test_git_command_failure(self, mock_run):
        """Test git command failure raises RuntimeError."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, ['git', 'rev-parse', 'HEAD'], stderr="git command failed")
        
        with pytest.raises(RuntimeError, match="Git command failed"):
            _run_git_command(['rev-parse', 'HEAD'])


class TestIsWorkingDirectoryClean:
    """Tests for the _is_working_directory_clean helper function."""
    
    @patch('codelog.commit._run_git_command')
    def test_clean_working_directory(self, mock_run_git):
        """Test when working directory is clean."""
        mock_run_git.return_value = ""
        
        result = _is_working_directory_clean()
        
        assert result is True
        mock_run_git.assert_called_once_with(['status', '--porcelain'], None)
    
    @patch('codelog.commit._run_git_command')
    def test_clean_working_directory_with_path(self, mock_run_git):
        """Test when working directory is clean with specific path."""
        mock_run_git.return_value = ""
        
        result = _is_working_directory_clean('/path/to/repo')
        
        assert result is True
        mock_run_git.assert_called_once_with(['status', '--porcelain'], '/path/to/repo')
    
    @patch('codelog.commit._run_git_command')
    def test_dirty_working_directory(self, mock_run_git):
        """Test when working directory has changes."""
        mock_run_git.return_value = "M  modified_file.py\n?? new_file.py"
        
        result = _is_working_directory_clean()
        
        assert result is False
        mock_run_git.assert_called_once_with(['status', '--porcelain'], None)


class TestGetMostRecentCommitHash:
    """Tests for the get_most_recent_commit_hash function."""
    
    @patch('codelog.commit._run_git_command')
    def test_get_commit_hash_success(self, mock_run_git):
        """Test successful retrieval of commit hash."""
        expected_hash = "abc123def456"
        mock_run_git.return_value = expected_hash
        
        result = get_most_recent_commit_hash()
        
        assert result == expected_hash
        mock_run_git.assert_called_once_with(['rev-parse', 'HEAD'], None)
    
    @patch('codelog.commit._run_git_command')
    def test_get_commit_hash_success_with_path(self, mock_run_git):
        """Test successful retrieval of commit hash with specific path."""
        expected_hash = "abc123def456"
        mock_run_git.return_value = expected_hash
        
        result = get_most_recent_commit_hash('/path/to/repo')
        
        assert result == expected_hash
        mock_run_git.assert_called_once_with(['rev-parse', 'HEAD'], '/path/to/repo')
    
    @patch('codelog.commit._run_git_command')
    def test_get_commit_hash_failure(self, mock_run_git):
        """Test failure to get commit hash."""
        mock_run_git.side_effect = RuntimeError("Not a git repository")
        
        with pytest.raises(RuntimeError, match="Not a git repository"):
            get_most_recent_commit_hash()


class TestGetCommitHash:
    """Tests for the get_commit_hash function."""
    
    @patch('codelog.commit._run_git_command')
    @patch('codelog.commit._is_working_directory_clean')
    def test_clean_working_directory(self, mock_is_clean, mock_run_git):
        """Test when working directory is clean."""
        mock_is_clean.return_value = True
        mock_run_git.return_value = "abc123def456"
        
        result = get_commit_hash()
        
        assert result == "abc123def456"
        mock_is_clean.assert_called_once_with(None)
        mock_run_git.assert_called_once_with(['rev-parse', 'HEAD'], None)
    
    @patch('codelog.commit._run_git_command')
    @patch('codelog.commit._is_working_directory_clean')
    def test_clean_working_directory_with_path(self, mock_is_clean, mock_run_git):
        """Test when working directory is clean with specific path."""
        mock_is_clean.return_value = True
        mock_run_git.return_value = "abc123def456"
        
        result = get_commit_hash('/path/to/repo')
        
        assert result == "abc123def456"
        mock_is_clean.assert_called_once_with('/path/to/repo')
        mock_run_git.assert_called_once_with(['rev-parse', 'HEAD'], '/path/to/repo')
    
    @patch('codelog.commit._is_working_directory_clean')
    def test_dirty_working_directory(self, mock_is_clean):
        """Test when working directory has changes."""
        mock_is_clean.return_value = False
        
        result = get_commit_hash()
        
        assert result is None
        mock_is_clean.assert_called_once_with(None)
    
    @patch('codelog.commit._run_git_command')
    @patch('codelog.commit._is_working_directory_clean')
    def test_git_command_failure(self, mock_is_clean, mock_run_git):
        """Test when git command fails."""
        mock_is_clean.return_value = True
        mock_run_git.side_effect = RuntimeError("Git command failed")
        
        with pytest.raises(RuntimeError, match="Git command failed"):
            get_commit_hash()


class TestEnsureCodeIsTracked:
    """Tests for the ensure_code_is_tracked function."""
    
    @patch('codelog.commit.get_commit_hash')
    def test_successful_tracking(self, mock_get_commit_hash):
        """Test when code is properly tracked."""
        expected_hash = "abc123def456"
        mock_get_commit_hash.return_value = expected_hash
        
        result = ensure_code_is_tracked()
        
        assert result == expected_hash
        mock_get_commit_hash.assert_called_once_with(None)
    
    @patch('codelog.commit.get_commit_hash')
    def test_successful_tracking_with_path(self, mock_get_commit_hash):
        """Test when code is properly tracked with specific path."""
        expected_hash = "abc123def456"
        mock_get_commit_hash.return_value = expected_hash
        
        result = ensure_code_is_tracked('/path/to/repo')
        
        assert result == expected_hash
        mock_get_commit_hash.assert_called_once_with('/path/to/repo')
    
    @patch('codelog.commit._run_git_command')
    @patch('codelog.commit.get_commit_hash')
    def test_uncommitted_changes_detected(self, mock_get_commit_hash, mock_run_git):
        """Test when uncommitted changes are detected."""
        mock_get_commit_hash.return_value = None
        mock_run_git.return_value = "M  modified_file.py\n?? new_file.py"
        
        with pytest.raises(RuntimeError, match="Uncommitted changes detected"):
            ensure_code_is_tracked()
        
        mock_get_commit_hash.assert_called_once_with(None)
        mock_run_git.assert_called_once_with(['status', '--short'], None)
    
    @patch('codelog.commit._run_git_command')
    @patch('codelog.commit.get_commit_hash')
    def test_uncommitted_changes_with_details(self, mock_get_commit_hash, mock_run_git):
        """Test error message includes details of uncommitted changes."""
        mock_get_commit_hash.return_value = None
        mock_run_git.return_value = "M  modified_file.py\n?? new_file.py"
        
        with pytest.raises(RuntimeError) as exc_info:
            ensure_code_is_tracked()
        
        error_message = str(exc_info.value)
        assert "Uncommitted changes detected:" in error_message
        assert "  M  modified_file.py" in error_message
        assert "  ?? new_file.py" in error_message
    
    @patch('codelog.commit._run_git_command')
    @patch('codelog.commit.get_commit_hash')
    def test_uncommitted_changes_with_path(self, mock_get_commit_hash, mock_run_git):
        """Test error message includes details of uncommitted changes with specific path."""
        mock_get_commit_hash.return_value = None
        mock_run_git.return_value = "M  modified_file.py\n?? new_file.py"
        
        with pytest.raises(RuntimeError) as exc_info:
            ensure_code_is_tracked('/path/to/repo')
        
        error_message = str(exc_info.value)
        assert "Uncommitted changes detected:" in error_message
        assert "  M  modified_file.py" in error_message
        assert "  ?? new_file.py" in error_message
        
        mock_get_commit_hash.assert_called_once_with('/path/to/repo')
        mock_run_git.assert_called_once_with(['status', '--short'], '/path/to/repo')
    
    @patch('codelog.commit._run_git_command')
    @patch('codelog.commit.get_commit_hash')
    def test_unknown_dirty_state(self, mock_get_commit_hash, mock_run_git):
        """Test when working directory is dirty but status is empty."""
        mock_get_commit_hash.return_value = None
        mock_run_git.return_value = ""
        
        with pytest.raises(RuntimeError, match="Working directory is not clean"):
            ensure_code_is_tracked()
    
    @patch('codelog.commit.get_commit_hash')
    def test_git_command_failure_in_ensure(self, mock_get_commit_hash):
        """Test when git command fails during ensure_code_is_tracked."""
        mock_get_commit_hash.return_value = None
        mock_get_commit_hash.side_effect = RuntimeError("Git command failed")
        
        with pytest.raises(RuntimeError, match="Git command failed"):
            ensure_code_is_tracked()


class TestIntegration:
    """Integration tests that test multiple functions together."""
    
    @patch('codelog.commit._run_git_command')
    def test_full_workflow_clean_repository(self, mock_run_git):
        """Test the full workflow with a clean repository."""
        # Mock responses for different git commands
        def mock_git_command(args, path=None):
            if args == ['status', '--porcelain']:
                return ""
            elif args == ['rev-parse', 'HEAD']:
                return "abc123def456"
            else:
                raise ValueError(f"Unexpected git command: {args}")
        
        mock_run_git.side_effect = mock_git_command
        
        # Test all functions
        assert _is_working_directory_clean() is True
        assert get_most_recent_commit_hash() == "abc123def456"
        assert get_commit_hash() == "abc123def456"
        assert ensure_code_is_tracked() == "abc123def456"
    
    @patch('codelog.commit._run_git_command')
    def test_full_workflow_dirty_repository(self, mock_run_git):
        """Test the full workflow with a dirty repository."""
        # Mock responses for different git commands
        def mock_git_command(args, path=None):
            if args == ['status', '--porcelain']:
                return "M  modified_file.py"
            elif args == ['status', '--short']:
                return "M  modified_file.py"
            elif args == ['rev-parse', 'HEAD']:
                return "abc123def456"
            else:
                raise ValueError(f"Unexpected git command: {args}")
        
        mock_run_git.side_effect = mock_git_command
        
        # Test all functions
        assert _is_working_directory_clean() is False
        assert get_most_recent_commit_hash() == "abc123def456"
        assert get_commit_hash() is None
        
        with pytest.raises(RuntimeError, match="Uncommitted changes detected"):
            ensure_code_is_tracked() 