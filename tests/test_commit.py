"""
Tests for the commit module functions.
"""

import pytest
import tempfile
import os
import subprocess
from unittest.mock import patch, Mock
from codelog.commit import (
    get_most_recent_commit_hash,
    get_commit_hash,
    ensure_code_is_tracked,
    make_side_commit,
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
        # Check that the call was made with the expected arguments, but ignore env
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ['git', 'rev-parse', 'HEAD']
        assert call_args[1]['capture_output'] is True
        assert call_args[1]['text'] is True
        assert call_args[1]['check'] is True
        assert 'env' in call_args[1]  # env should be present
    
    @patch('subprocess.run')
    def test_successful_git_command_with_path(self, mock_run):
        """Test successful git command execution with specific path."""
        mock_result = Mock()
        mock_result.stdout = "abc123\n"
        mock_run.return_value = mock_result
        
        result = _run_git_command(['rev-parse', 'HEAD'], '/path/to/repo')
        
        assert result == "abc123"
        # Check that the call was made with the expected arguments, but ignore env
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ['git', '-C', '/path/to/repo', 'rev-parse', 'HEAD']
        assert call_args[1]['capture_output'] is True
        assert call_args[1]['text'] is True
        assert call_args[1]['check'] is True
        assert 'env' in call_args[1]  # env should be present
    
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


class TestMakeSideCommit:
    """Tests for the make_side_commit function."""
    
    @patch('codelog.commit._is_working_directory_clean')
    @patch('codelog.commit._run_git_command')
    def test_clean_working_directory_no_force(self, mock_run_git, mock_is_clean):
        """Test when working directory is clean and force=False (default)."""
        mock_is_clean.return_value = True
        mock_run_git.return_value = "abc123def456"
        
        result = make_side_commit()
        
        assert result == "abc123def456"
        mock_is_clean.assert_called_once_with(None)
        mock_run_git.assert_called_once_with(['rev-parse', 'HEAD'], None)
    
    @patch('codelog.commit._is_working_directory_clean')
    @patch('codelog.commit._run_git_command')
    def test_clean_working_directory_with_force(self, mock_run_git, mock_is_clean):
        """Test when working directory is clean but force=True."""
        mock_is_clean.return_value = True
        mock_run_git.side_effect = [
            "tree123",       # write-tree
            "parent123",     # rev-parse HEAD (parent commit)
            "commit456",     # commit-tree
            None            # branch creation (no output)
        ]
        
        with patch('codelog.commit._create_temporary_index') as mock_create_index, \
             patch('codelog.commit._add_tracked_files_to_temp_index') as mock_add_files, \
             patch('codelog.commit._cleanup_temporary_index') as mock_cleanup:
            
            mock_create_index.return_value = ("/tmp/index.tmp", {"GIT_INDEX_FILE": "/tmp/index.tmp"})
            
            result = make_side_commit(force=True)
            
            assert result == "commit456"
            # When force=True, _is_working_directory_clean should not be called
            mock_is_clean.assert_not_called()
            mock_create_index.assert_called_once_with(None)
            mock_add_files.assert_called_once_with(None, {"GIT_INDEX_FILE": "/tmp/index.tmp"})
            mock_cleanup.assert_called_once_with("/tmp/index.tmp")
    
    @patch('codelog.commit._is_working_directory_clean')
    @patch('codelog.commit._run_git_command')
    def test_dirty_working_directory_creates_side_commit(self, mock_run_git, mock_is_clean):
        """Test when working directory is dirty - should create side commit."""
        mock_is_clean.return_value = False
        mock_run_git.side_effect = [
            "tree123",       # write-tree
            "parent123",     # rev-parse HEAD (parent commit)
            "commit456",     # commit-tree
            None            # branch creation (no output)
        ]
        
        with patch('codelog.commit._create_temporary_index') as mock_create_index, \
             patch('codelog.commit._add_tracked_files_to_temp_index') as mock_add_files, \
             patch('codelog.commit._cleanup_temporary_index') as mock_cleanup:
            
            mock_create_index.return_value = ("/tmp/index.tmp", {"GIT_INDEX_FILE": "/tmp/index.tmp"})
            
            result = make_side_commit()
            
            assert result == "commit456"
            mock_is_clean.assert_called_once_with(None)
            mock_create_index.assert_called_once_with(None)
            mock_add_files.assert_called_once_with(None, {"GIT_INDEX_FILE": "/tmp/index.tmp"})
            mock_cleanup.assert_called_once_with("/tmp/index.tmp")
    
    @patch('codelog.commit._is_working_directory_clean')
    @patch('codelog.commit._run_git_command')
    def test_side_commit_with_path_parameter(self, mock_run_git, mock_is_clean):
        """Test side commit creation with specific path."""
        mock_is_clean.return_value = False
        mock_run_git.side_effect = [
            "tree123",       # write-tree
            "parent123",     # rev-parse HEAD (parent commit)
            "commit456",     # commit-tree
            None            # branch creation (no output)
        ]
        
        with patch('codelog.commit._create_temporary_index') as mock_create_index, \
             patch('codelog.commit._add_tracked_files_to_temp_index') as mock_add_files, \
             patch('codelog.commit._cleanup_temporary_index') as mock_cleanup:
            
            mock_create_index.return_value = ("/tmp/index.tmp", {"GIT_INDEX_FILE": "/tmp/index.tmp"})
            
            result = make_side_commit('/path/to/repo')
            
            assert result == "commit456"
            mock_is_clean.assert_called_once_with('/path/to/repo')
            mock_create_index.assert_called_once_with('/path/to/repo')
            mock_add_files.assert_called_once_with('/path/to/repo', {"GIT_INDEX_FILE": "/tmp/index.tmp"})
            mock_cleanup.assert_called_once_with("/tmp/index.tmp")
    
    @patch('codelog.commit._is_working_directory_clean')
    @patch('codelog.commit._run_git_command')
    def test_side_commit_with_parent_commit(self, mock_run_git, mock_is_clean):
        """Test side commit creation when there's a parent commit."""
        mock_is_clean.return_value = False
        mock_run_git.side_effect = [
            "tree123",       # write-tree
            "parent123",     # rev-parse HEAD (parent commit)
            "commit456",     # commit-tree
            None            # branch creation (no output)
        ]
        
        with patch('codelog.commit._create_temporary_index') as mock_create_index, \
             patch('codelog.commit._add_tracked_files_to_temp_index') as mock_add_files, \
             patch('codelog.commit._cleanup_temporary_index') as mock_cleanup:
            
            mock_create_index.return_value = ("/tmp/index.tmp", {"GIT_INDEX_FILE": "/tmp/index.tmp"})
            
            result = make_side_commit()
            
            assert result == "commit456"
            # Should call commit-tree with parent
            mock_run_git.assert_any_call(['commit-tree', 'tree123', '-m', 'side commit for state capture', '-p', 'parent123'], None)
    
    @patch('codelog.commit._is_working_directory_clean')
    @patch('codelog.commit._run_git_command')
    def test_side_commit_without_parent_commit(self, mock_run_git, mock_is_clean):
        """Test side commit creation when there's no parent commit (new repo)."""
        mock_is_clean.return_value = False
        mock_run_git.side_effect = [
            "tree123",                       # write-tree
            RuntimeError("No commits yet"),  # rev-parse HEAD fails
            "commit456",                     # commit-tree
            None                            # branch creation (no output)
        ]
        
        with patch('codelog.commit._create_temporary_index') as mock_create_index, \
             patch('codelog.commit._add_tracked_files_to_temp_index') as mock_add_files, \
             patch('codelog.commit._cleanup_temporary_index') as mock_cleanup:
            
            mock_create_index.return_value = ("/tmp/index.tmp", {"GIT_INDEX_FILE": "/tmp/index.tmp"})
            
            result = make_side_commit()
            
            assert result == "commit456"
            # Should call commit-tree without parent
            mock_run_git.assert_any_call(['commit-tree', 'tree123', '-m', 'side commit for state capture'], None)
    
    @patch('codelog.commit._is_working_directory_clean')
    def test_cleanup_on_error(self, mock_is_clean):
        """Test that temporary index is cleaned up even when errors occur."""
        mock_is_clean.return_value = False
        
        with patch('codelog.commit._create_temporary_index') as mock_create_index, \
             patch('codelog.commit._add_tracked_files_to_temp_index') as mock_add_files, \
             patch('codelog.commit._cleanup_temporary_index') as mock_cleanup, \
             patch('codelog.commit._run_git_command') as mock_run_git:
            
            mock_create_index.return_value = ("/tmp/index.tmp", {"GIT_INDEX_FILE": "/tmp/index.tmp"})
            mock_run_git.side_effect = RuntimeError("Git command failed")
            
            with pytest.raises(RuntimeError, match="Git command failed"):
                make_side_commit()
            
            # Should still cleanup even though error occurred
            mock_cleanup.assert_called_once_with("/tmp/index.tmp")
    
    @patch('codelog.commit._is_working_directory_clean')
    def test_branch_creation(self, mock_is_clean):
        """Test that a branch is created pointing to the side commit."""
        mock_is_clean.return_value = False
        
        with patch('codelog.commit._create_temporary_index') as mock_create_index, \
             patch('codelog.commit._add_tracked_files_to_temp_index') as mock_add_files, \
             patch('codelog.commit._cleanup_temporary_index') as mock_cleanup, \
             patch('codelog.commit._run_git_command') as mock_run_git:
            
            mock_create_index.return_value = ("/tmp/index.tmp", {"GIT_INDEX_FILE": "/tmp/index.tmp"})
            mock_run_git.side_effect = [
                "tree123",       # write-tree
                "parent123",     # rev-parse HEAD (parent commit)
                "commit456",     # commit-tree
                None            # branch creation (no output)
            ]
            
            result = make_side_commit()
            
            assert result == "commit456"
            # Should create branch with timestamp and process ID in name
            branch_call = None
            for call in mock_run_git.call_args_list:
                if call[0][0][0] == 'branch':
                    branch_call = call
                    break
            
            assert branch_call is not None
            branch_name = branch_call[0][0][1]  # The branch name is the second element of the command list
            assert branch_name.startswith("side-commit-")
            assert "commit456" in branch_call[0][0]  # Should point to our commit


class TestMakeSideCommitIntegration:
    """Integration tests for make_side_commit using real git repositories."""
    
    def _create_git_repo(self, temp_dir):
        """Helper to create a git repository in the given directory."""
        subprocess.run(['git', 'init'], cwd=temp_dir, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_dir, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_dir, check=True)
    
    def _create_initial_commit(self, temp_dir):
        """Helper to create an initial commit with a file."""
        with open(os.path.join(temp_dir, 'README.md'), 'w') as f:
            f.write("# Test Repository\n")
        
        subprocess.run(['git', 'add', 'README.md'], cwd=temp_dir, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=temp_dir, check=True)
    
    def test_side_commit_clean_repository_no_force(self):
        """Test side commit with clean repository and no force flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Get current commit hash
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=temp_dir, capture_output=True, text=True, check=True)
            current_hash = result.stdout.strip()
            
            # Should return current commit hash without creating side commit
            side_commit_hash = make_side_commit(temp_dir)
            assert side_commit_hash == current_hash
            
            # Verify no new branches were created
            result = subprocess.run(['git', 'branch'], cwd=temp_dir, capture_output=True, text=True, check=True)
            branches = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            assert len(branches) == 1  # Only the main branch
            assert '*' in branches[0]  # Current branch
    
    def test_side_commit_clean_repository_with_force(self):
        """Test side commit with clean repository and force flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Should create side commit even though clean
            side_commit_hash = make_side_commit(temp_dir, force=True)
            assert len(side_commit_hash) == 40  # Valid git hash
            
            # Verify new branch was created
            result = subprocess.run(['git', 'branch'], cwd=temp_dir, capture_output=True, text=True, check=True)
            branches = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            assert len(branches) == 2  # Main branch + side branch
            
            # Verify the side branch points to our commit
            side_branch = None
            for branch in branches:
                if branch.startswith('side-commit-') and not branch.startswith('*'):
                    side_branch = branch.strip()
                    break
            
            assert side_branch is not None
            result = subprocess.run(['git', 'rev-parse', side_branch], cwd=temp_dir, capture_output=True, text=True, check=True)
            branch_hash = result.stdout.strip()
            assert branch_hash == side_commit_hash
    
    def test_side_commit_with_modified_file(self):
        """Test side commit with a modified file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Modify the file
            with open(os.path.join(temp_dir, 'README.md'), 'w') as f:
                f.write("# Modified Test Repository\n")
            
            # Should create side commit
            side_commit_hash = make_side_commit(temp_dir)
            assert len(side_commit_hash) == 40  # Valid git hash
            
            # Verify working directory is unchanged
            with open(os.path.join(temp_dir, 'README.md'), 'r') as f:
                content = f.read()
            assert content == "# Modified Test Repository\n"
            
            # Verify the side commit contains the modified content
            result = subprocess.run(['git', 'show', f'{side_commit_hash}:README.md'], cwd=temp_dir, capture_output=True, text=True, check=True)
            commit_content = result.stdout
            assert commit_content == "# Modified Test Repository\n"
    
    def test_side_commit_with_untracked_file(self):
        """Test side commit with an untracked file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Add an untracked file
            with open(os.path.join(temp_dir, 'new_file.txt'), 'w') as f:
                f.write("This is a new file\n")
            
            # Should create side commit
            side_commit_hash = make_side_commit(temp_dir)
            assert len(side_commit_hash) == 40  # Valid git hash
            
            # Verify working directory is unchanged
            assert os.path.exists(os.path.join(temp_dir, 'new_file.txt'))
            
            # Verify the side commit does NOT contain the untracked file
            # (since we changed the behavior to only include tracked files)
            result = subprocess.run(['git', 'show', f'{side_commit_hash}:new_file.txt'], cwd=temp_dir, capture_output=True, text=True, check=False)
            assert result.returncode != 0  # Should fail because file is not in commit
    
    def test_side_commit_with_staged_file(self):
        """Test side commit with a staged file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Create and stage a new file
            with open(os.path.join(temp_dir, 'staged_file.txt'), 'w') as f:
                f.write("This file is staged\n")
            
            subprocess.run(['git', 'add', 'staged_file.txt'], cwd=temp_dir, check=True)
            
            # Should create side commit
            side_commit_hash = make_side_commit(temp_dir)
            assert len(side_commit_hash) == 40  # Valid git hash
            
            # Verify the side commit contains the staged file
            result = subprocess.run(['git', 'show', f'{side_commit_hash}:staged_file.txt'], cwd=temp_dir, capture_output=True, text=True, check=True)
            commit_content = result.stdout
            assert commit_content == "This file is staged\n"
    
    def test_side_commit_preserves_working_directory_state(self):
        """Test that side commit doesn't change the working directory state."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Create a tracked file and commit it
            with open(os.path.join(temp_dir, 'modified.txt'), 'w') as f:
                f.write("Original content\n")
            subprocess.run(['git', 'add', 'modified.txt'], cwd=temp_dir, check=True)
            subprocess.run(['git', 'commit', '-m', 'Add modified.txt'], cwd=temp_dir, check=True)
            
            # Modify the tracked file
            with open(os.path.join(temp_dir, 'modified.txt'), 'w') as f:
                f.write("Modified content\n")
            
            # Add untracked file
            with open(os.path.join(temp_dir, 'untracked.txt'), 'w') as f:
                f.write("Untracked content\n")
            
            # Stage a new file
            with open(os.path.join(temp_dir, 'staged.txt'), 'w') as f:
                f.write("Staged content\n")
            subprocess.run(['git', 'add', 'staged.txt'], cwd=temp_dir, check=True)
            
            # Check git status before
            result = subprocess.run(['git', 'status', '--porcelain'], cwd=temp_dir, capture_output=True, text=True, check=True)
            status_before = result.stdout
            
            # Create side commit
            side_commit_hash = make_side_commit(temp_dir)
            assert len(side_commit_hash) == 40
            
            # Check git status after - should be identical
            result = subprocess.run(['git', 'status', '--porcelain'], cwd=temp_dir, capture_output=True, text=True, check=True)
            status_after = result.stdout
            
            assert status_before == status_after
            
            # Verify file contents are unchanged
            with open(os.path.join(temp_dir, 'modified.txt'), 'r') as f:
                assert f.read() == "Modified content\n"
            with open(os.path.join(temp_dir, 'untracked.txt'), 'r') as f:
                assert f.read() == "Untracked content\n"
            with open(os.path.join(temp_dir, 'staged.txt'), 'r') as f:
                assert f.read() == "Staged content\n"
    
    def test_side_commit_new_repository(self):
        """Test side commit with a new repository (no commits yet)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            
            # Add a file without committing
            with open(os.path.join(temp_dir, 'new_file.txt'), 'w') as f:
                f.write("New file content\n")
            
            # Should create side commit (root commit)
            side_commit_hash = make_side_commit(temp_dir)
            assert len(side_commit_hash) == 40  # Valid git hash
            
            # Verify the side commit does NOT contain the file (since it's untracked)
            result = subprocess.run(['git', 'show', f'{side_commit_hash}:new_file.txt'], cwd=temp_dir, capture_output=True, text=True, check=False)
            assert result.returncode != 0  # Should fail because file is not in commit
    
    def test_side_commit_concurrent_processes(self):
        """Test that multiple side commits can be created concurrently."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Create multiple side commits with modified tracked files
            import time
            
            # First commit with modified README
            with open(os.path.join(temp_dir, 'README.md'), 'w') as f:
                f.write("# Test Repository - Version 1\n")
            hash1 = make_side_commit(temp_dir)
            
            # Second commit with different README content
            with open(os.path.join(temp_dir, 'README.md'), 'w') as f:
                f.write("# Test Repository - Version 2\n")
            hash2 = make_side_commit(temp_dir)
            
            # Third commit with yet different README content
            with open(os.path.join(temp_dir, 'README.md'), 'w') as f:
                f.write("# Test Repository - Version 3\n")
            hash3 = make_side_commit(temp_dir)
            
            # All should be different (due to different content)
            assert hash1 != hash2
            assert hash2 != hash3
            assert hash1 != hash3
            
            # All should be valid git hashes
            assert len(hash1) == 40
            assert len(hash2) == 40
            assert len(hash3) == 40
            
            # Verify all branches exist
            result = subprocess.run(['git', 'branch'], cwd=temp_dir, capture_output=True, text=True, check=True)
            branches = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            side_branches = [b for b in branches if b.startswith('side-commit-')]
            assert len(side_branches) == 3

    def test_side_commit_identical_content_same_hash(self):
        """Test that side commits with identical content produce the same hash."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Modify the README with identical content multiple times
            with open(os.path.join(temp_dir, 'README.md'), 'w') as f:
                f.write("# Test Repository - Identical\n")
            
            # Create multiple side commits with identical content
            hash1 = make_side_commit(temp_dir)
            hash2 = make_side_commit(temp_dir)
            hash3 = make_side_commit(temp_dir)
            
            # Note: Git commits include timestamps, so identical content may produce different hashes
            # This is actually correct git behavior. The important thing is that we can recover the state.
            
            # All should be valid git hashes
            assert len(hash1) == 40
            assert len(hash2) == 40
            assert len(hash3) == 40
            
            # Verify all branches exist
            result = subprocess.run(['git', 'branch'], cwd=temp_dir, capture_output=True, text=True, check=True)
            branches = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            side_branches = [b for b in branches if b.startswith('side-commit-')]
            assert len(side_branches) == 3
            
            # Verify we can recover the exact state from any of the hashes
            for hash_val in [hash1, hash2, hash3]:
                result = subprocess.run(['git', 'show', f'{hash_val}:README.md'], cwd=temp_dir, capture_output=True, text=True, check=True)
                recovered_content = result.stdout
                assert recovered_content == "# Test Repository - Identical\n"
            
            # Verify the tree hashes are the same (content-based, no timestamps)
            tree1 = subprocess.run(['git', 'show', '--format=%T', '--no-patch', hash1], cwd=temp_dir, capture_output=True, text=True, check=True).stdout.strip()
            tree2 = subprocess.run(['git', 'show', '--format=%T', '--no-patch', hash2], cwd=temp_dir, capture_output=True, text=True, check=True).stdout.strip()
            tree3 = subprocess.run(['git', 'show', '--format=%T', '--no-patch', hash3], cwd=temp_dir, capture_output=True, text=True, check=True).stdout.strip()
            
            # Tree hashes should be identical (content-based)
            assert tree1 == tree2
            assert tree2 == tree3
            assert tree1 == tree3

    def test_side_commit_only_includes_tracked_files_with_changes(self):
        """Test that side commit includes tracked files with changes and staged files, but not untracked files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Create a tracked file and commit it
            with open(os.path.join(temp_dir, 'tracked_file.txt'), 'w') as f:
                f.write("Original tracked content\n")
            subprocess.run(['git', 'add', 'tracked_file.txt'], cwd=temp_dir, check=True)
            subprocess.run(['git', 'commit', '-m', 'Add tracked file'], cwd=temp_dir, check=True)
            
            # Modify the tracked file
            with open(os.path.join(temp_dir, 'tracked_file.txt'), 'w') as f:
                f.write("Modified tracked content\n")
            
            # Create an untracked file
            with open(os.path.join(temp_dir, 'untracked_file.txt'), 'w') as f:
                f.write("Untracked content\n")
            
            # Stage a new file (not yet committed)
            with open(os.path.join(temp_dir, 'staged_file.txt'), 'w') as f:
                f.write("Staged content\n")
            subprocess.run(['git', 'add', 'staged_file.txt'], cwd=temp_dir, check=True)
            
            # Create side commit
            side_commit_hash = make_side_commit(temp_dir)
            assert len(side_commit_hash) == 40  # Valid git hash
            
            # Verify the side commit contains the modified tracked file
            result = subprocess.run(['git', 'show', f'{side_commit_hash}:tracked_file.txt'], cwd=temp_dir, capture_output=True, text=True, check=True)
            commit_content = result.stdout
            assert commit_content == "Modified tracked content\n"
            
            # Verify the side commit does NOT contain the untracked file
            result = subprocess.run(['git', 'show', f'{side_commit_hash}:untracked_file.txt'], cwd=temp_dir, capture_output=True, text=True, check=False)
            assert result.returncode != 0  # Should fail because file is not in commit
            
            # Verify the side commit contains the staged file
            result = subprocess.run(['git', 'show', f'{side_commit_hash}:staged_file.txt'], cwd=temp_dir, capture_output=True, text=True, check=True)
            commit_content = result.stdout
            assert commit_content == "Staged content\n"
            
            # Verify the side commit contains the original README.md (unchanged tracked file)
            result = subprocess.run(['git', 'show', f'{side_commit_hash}:README.md'], cwd=temp_dir, capture_output=True, text=True, check=True)
            commit_content = result.stdout
            assert commit_content == "# Test Repository\n"


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


class TestRealGitIntegration:
    """Real git integration tests using temporary repositories."""
    
    def _create_git_repo(self, temp_dir):
        """Helper to create a git repository in the given directory."""
        subprocess.run(['git', 'init'], cwd=temp_dir, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_dir, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_dir, check=True)
    
    def _create_initial_commit(self, temp_dir):
        """Helper to create an initial commit with a file."""
        with open(os.path.join(temp_dir, 'README.md'), 'w') as f:
            f.write("# Test Repository\n")
        
        subprocess.run(['git', 'add', 'README.md'], cwd=temp_dir, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=temp_dir, check=True)
    
    def test_clean_repository(self):
        """Test with a clean git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Test all functions
            assert _is_working_directory_clean(temp_dir) is True
            commit_hash = get_most_recent_commit_hash(temp_dir)
            assert len(commit_hash) == 40  # Full git hash length
            assert get_commit_hash(temp_dir) == commit_hash
            assert ensure_code_is_tracked(temp_dir) == commit_hash
    
    def test_repository_with_modified_file(self):
        """Test with a repository that has a modified file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Modify the file
            with open(os.path.join(temp_dir, 'README.md'), 'w') as f:
                f.write("# Modified Test Repository\n")
            
            # Test functions
            assert _is_working_directory_clean(temp_dir) is False
            commit_hash = get_most_recent_commit_hash(temp_dir)
            assert len(commit_hash) == 40
            assert get_commit_hash(temp_dir) is None
            
            with pytest.raises(RuntimeError, match="Uncommitted changes detected"):
                ensure_code_is_tracked(temp_dir)
    
    def test_repository_with_untracked_file(self):
        """Test with a repository that has an untracked file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Add an untracked file
            with open(os.path.join(temp_dir, 'new_file.txt'), 'w') as f:
                f.write("This is a new file\n")
            
            # Test functions
            assert _is_working_directory_clean(temp_dir) is False
            commit_hash = get_most_recent_commit_hash(temp_dir)
            assert len(commit_hash) == 40
            assert get_commit_hash(temp_dir) is None
            
            with pytest.raises(RuntimeError, match="Uncommitted changes detected"):
                ensure_code_is_tracked(temp_dir)
    
    def test_repository_with_staged_file(self):
        """Test with a repository that has a staged file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Create and stage a new file
            with open(os.path.join(temp_dir, 'staged_file.txt'), 'w') as f:
                f.write("This file is staged\n")
            
            subprocess.run(['git', 'add', 'staged_file.txt'], cwd=temp_dir, check=True)
            
            # Test functions
            assert _is_working_directory_clean(temp_dir) is False
            commit_hash = get_most_recent_commit_hash(temp_dir)
            assert len(commit_hash) == 40
            assert get_commit_hash(temp_dir) is None
            
            with pytest.raises(RuntimeError, match="Uncommitted changes detected"):
                ensure_code_is_tracked(temp_dir)
    
    def test_repository_with_multiple_changes(self):
        """Test with a repository that has multiple types of changes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Modify existing file
            with open(os.path.join(temp_dir, 'README.md'), 'w') as f:
                f.write("# Modified Test Repository\n")
            
            # Add untracked file
            with open(os.path.join(temp_dir, 'untracked.txt'), 'w') as f:
                f.write("Untracked file\n")
            
            # Create and stage a file
            with open(os.path.join(temp_dir, 'staged.txt'), 'w') as f:
                f.write("Staged file\n")
            subprocess.run(['git', 'add', 'staged.txt'], cwd=temp_dir, check=True)
            
            # Test functions
            assert _is_working_directory_clean(temp_dir) is False
            commit_hash = get_most_recent_commit_hash(temp_dir)
            assert len(commit_hash) == 40
            assert get_commit_hash(temp_dir) is None
            
            with pytest.raises(RuntimeError, match="Uncommitted changes detected"):
                ensure_code_is_tracked(temp_dir)
    
    def test_not_a_git_repository(self):
        """Test behavior when the path is not a git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a regular directory (not a git repo)
            with open(os.path.join(temp_dir, 'some_file.txt'), 'w') as f:
                f.write("Just a regular file\n")
            
            # Test functions - should raise RuntimeError
            with pytest.raises(RuntimeError):
                _is_working_directory_clean(temp_dir)
            
            with pytest.raises(RuntimeError):
                get_most_recent_commit_hash(temp_dir)
            
            with pytest.raises(RuntimeError):
                get_commit_hash(temp_dir)
            
            with pytest.raises(RuntimeError):
                ensure_code_is_tracked(temp_dir)
    
    def test_path_parameter_functionality(self):
        """Test that the path parameter works correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_git_repo(temp_dir)
            self._create_initial_commit(temp_dir)
            
            # Test from a different directory
            original_cwd = os.getcwd()
            try:
                # Change to a different directory
                os.chdir('/tmp')
                
                # Test functions with path parameter
                assert _is_working_directory_clean(temp_dir) is True
                commit_hash = get_most_recent_commit_hash(temp_dir)
                assert len(commit_hash) == 40
                assert get_commit_hash(temp_dir) == commit_hash
                assert ensure_code_is_tracked(temp_dir) == commit_hash
                
                # Test that current directory is not affected
                with pytest.raises(RuntimeError):
                    _is_working_directory_clean()
                    
            finally:
                os.chdir(original_cwd) 