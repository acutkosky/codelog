'''
Git commit tracking utilities for experiment reproducibility.

This module provides functions to ensure that code is properly tracked in git
before running experiments. It helps maintain reproducibility by verifying
that all changes are committed and providing access to commit hashes for
experiment logging and version tracking.

Key functions:
- get_most_recent_commit_hash(): Get the current commit hash regardless of working directory state
- get_commit_hash(): Get commit hash only if working directory is clean
- ensure_code_is_tracked(): Verify all changes are committed and return commit hash
- make_side_commit(): Create a side commit to capture current state without affecting current branch

All functions raise RuntimeError if not in a git repository or if git commands fail.
'''

import subprocess
import time
import os
import tempfile
import shutil
import uuid
from pathlib import Path
from typing import Optional


def _run_git_command(args: list[str], path: Optional[str] = None, env: Optional[dict] = None) -> str:
    '''Runs a git command and returns the output.
    
    Args:
        args: List of command arguments (e.g., ['rev-parse', 'HEAD'])
        path: Optional path to run the git command in. If None, uses current directory.
        env: Optional environment variables to use for the command.
        
    Returns:
        str: The command output (stripped of whitespace)
        
    Raises:
        RuntimeError: If the git command fails or if not in a git repository.
    '''
    try:
        cmd = ['git'] + args
        if path:
            cmd = ['git', '-C', path] + args
        
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            env=process_env
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git command failed: {e.stderr}") from e


def _get_git_dir(path: Optional[str] = None) -> Path:
    '''Get the .git directory path.
    
    Args:
        path: Optional path to get git dir from. If None, uses current directory.
        
    Returns:
        Path: The absolute path to the .git directory.
    '''
    git_dir_str = _run_git_command(['rev-parse', '--git-dir'], path)
    git_dir = Path(git_dir_str)
    if not git_dir.is_absolute():
        repo_path = Path(path) if path else Path.cwd()
        git_dir = repo_path / git_dir
    return git_dir.resolve()


def _create_temporary_index(path: Optional[str] = None) -> tuple[str, dict]:
    '''Create a temporary index file and return its path and environment.
    
    Args:
        path: Optional path to create index in. If None, uses current directory.
        
    Returns:
        tuple: (temp_index_path, env_dict) for using the temporary index.
    '''
    git_dir = _get_git_dir(path)
    instance_id = str(uuid.uuid4())[:8]
    
    # Create temporary index file with unique name
    temp_index = git_dir / f"index.tmp.{instance_id}.{os.getpid()}"
    
    # Copy current index to temporary index if it exists and is not empty
    current_index = git_dir / "index"
    if current_index.exists() and current_index.stat().st_size > 0:
        shutil.copy2(current_index, temp_index)
    else:
        # Create a proper empty index by running git read-tree with empty tree
        try:
            # Create an empty tree object
            empty_tree = _run_git_command(['mktree'], path)
            # Create an empty index pointing to the empty tree
            _run_git_command(['read-tree', empty_tree], path, {"GIT_INDEX_FILE": str(temp_index)})
        except RuntimeError:
            # If that fails, just create an empty file and let git handle it
            temp_index.touch()
    
    # Environment to use this temporary index
    env = {"GIT_INDEX_FILE": str(temp_index)}
    
    return str(temp_index), env


def _cleanup_temporary_index(temp_index_path: str) -> None:
    '''Remove the temporary index file.
    
    Args:
        temp_index_path: Path to the temporary index file to remove.
    '''
    try:
        os.unlink(temp_index_path)
    except FileNotFoundError:
        pass  # Already cleaned up


def _add_all_files_to_temp_index(path: Optional[str] = None, env: Optional[dict] = None) -> None:
    '''Add all files (including untracked) to the temporary index.
    
    Args:
        path: Optional path to add files from. If None, uses current directory.
        env: Environment dict with GIT_INDEX_FILE set.
    '''
    # Add all tracked and modified files (this might fail if no tracked files exist)
    try:
        _run_git_command(['add', '-u'], path, env)
    except RuntimeError:
        # No tracked files to update, which is fine
        pass
    
    # Add all untracked files
    try:
        # Get list of untracked files
        untracked_output = _run_git_command(['ls-files', '--others', '--exclude-standard'], path)
        untracked_files = [f.strip() for f in untracked_output.split('\n') if f.strip()]
        
        # Add each untracked file individually to avoid issues with special characters
        for file_path in untracked_files:
            if file_path:  # Skip empty lines
                try:
                    _run_git_command(['add', file_path], path, env)
                except RuntimeError:
                    # Skip files that can't be added (e.g., directories, special files)
                    continue
    except RuntimeError:
        # No untracked files or other error
        pass


def _add_tracked_files_to_temp_index(path: Optional[str] = None, env: Optional[dict] = None) -> None:
    '''Add tracked files with changes and staged files to the temporary index.
    
    Args:
        path: Optional path to add files from. If None, uses current directory.
        env: Environment dict with GIT_INDEX_FILE set.
    '''
    # Add all tracked files with changes (unstaged and staged)
    try:
        _run_git_command(['add', '-u'], path, env)
    except RuntimeError:
        # No tracked files to update, which is fine
        pass


def _is_working_directory_clean(path: Optional[str] = None) -> bool:
    '''Checks if the git working directory is clean.
    
    Args:
        path: Optional path to check. If None, uses current directory.
        
    Returns:
        bool: True if working directory is clean (no unstaged changes, no untracked files),
              False otherwise.
    '''
    status_output = _run_git_command(['status', '--porcelain'], path)
    return not bool(status_output.strip())


def _get_current_branch_or_commit(path: Optional[str] = None) -> str:
    '''Get the current branch name or short commit hash if in detached HEAD state.
    
    Args:
        path: Optional path to check. If None, uses current directory.
        
    Returns:
        str: Current branch name, or short commit hash if in detached HEAD state.
    '''
    try:
        # Try to get current branch name
        branch_name = _run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'], path)
        if branch_name == 'HEAD':
            # We're in detached HEAD state, get short commit hash
            return _run_git_command(['rev-parse', '--short', 'HEAD'], path)
        return branch_name
    except RuntimeError:
        # If we can't get branch name or commit hash (e.g., no commits yet),
        # return a default value
        return "new"


def get_most_recent_commit_hash(path: Optional[str] = None) -> str:
    '''Returns the most recent commit hash of the codebase.
    
    Args:
        path: Optional path to get commit hash from. If None, uses current directory.
        
    Returns:
        str: The full commit hash of the most recent commit on the current branch.
        
    Raises:
        RuntimeError: If not in a git repository or git command fails.
    '''
    return _run_git_command(['rev-parse', 'HEAD'], path)


def get_commit_hash(path: Optional[str] = None) -> Optional[str]:
    '''Returns the current commit hash of the codebase.
    
    Returns the commit hash only if the working directory is clean
    (no unstaged changes, no untracked files). Otherwise returns None.
    
    Args:
        path: Optional path to check. If None, uses current directory.
        
    Returns:
        Optional[str]: The current commit hash if working directory is clean,
                      None if there are uncommitted changes.
                      
    Raises:
        RuntimeError: If not in a git repository or git command fails.
    '''
    if not _is_working_directory_clean(path):
        return None
    return _run_git_command(['rev-parse', 'HEAD'], path)


def ensure_code_is_tracked(path: Optional[str] = None) -> str:
    '''Ensures that the current code is checked in with git.
    
    Raises an error if there are uncommitted changes (unstaged changes
    or untracked files). Returns the commit hash if the working directory
    is clean.
    
    Args:
        path: Optional path to check. If None, uses current directory.
        
    Returns:
        str: The commit hash of the codebase.
        
    Raises:
        RuntimeError: If there are uncommitted changes or if not in a git repository.
    '''
    commit_hash = get_commit_hash(path)
    if commit_hash is None:
        # Get detailed status information for the error message
        status_output = _run_git_command(['status', '--short'], path)
        status_lines = [line for line in status_output.split('\n') if line.strip()]
        
        if status_lines:
            raise RuntimeError(
                f"Uncommitted changes detected:\n" + 
                "\n".join(f"  {line}" for line in status_lines)
            )
        else:
            raise RuntimeError("Working directory is not clean")
    
    return commit_hash


def make_side_commit(path: Optional[str] = None, prefix: str = "",force: bool = False) -> str:
    '''Checks in the current code into a new branch with a short unique name.
    The current file contents of the directory are not changed at any time, and the
    current git state is not changed (with the exception of the new branch).

    The commit hash of this "side commit" is returned. Only tracked files with changes
    (unstaged or staged) are included in the side commit; untracked files are ignored.

    This way, in the future we can recover the current state of the codebase from
    this hash, but we do not create extra commits on the current branch.

    This function is robust to simultaneous calls from multiple processes.
    
    Args:
        path: Optional path to make the side commit in. If None, uses current directory.
        prefix: Optional prefix to prepend to the branch name. Defaults to empty string.
        force: If True, always create a side commit even if working directory is clean.
               If False, return current commit hash if working directory is clean.
        
    Returns:
        str: The commit hash of the side commit (or current commit if clean and not forced).
        
    Raises:
        RuntimeError: If not in a git repository or git command fails.
    '''
    # If not forced and working directory is clean, return current commit hash
    if not force and _is_working_directory_clean(path):
        return _run_git_command(['rev-parse', 'HEAD'], path)
    
    # Get current branch name or short commit hash
    current_branch_or_commit = _get_current_branch_or_commit(path)
    
    # Generate unique branch name using timestamp and process ID
    timestamp = int(time.time() * 1000000)  # Use microseconds for more uniqueness
    process_id = os.getpid()
    branch_name = f"{prefix}_{current_branch_or_commit}_side-commit_{timestamp}_{process_id}"
    
    # Create temporary index for this operation
    temp_index_path, index_env = _create_temporary_index(path)
    
    try:
        # Step 1: Add only tracked files with changes to temporary index
        _add_tracked_files_to_temp_index(path, index_env)
        
        # Step 2: Create tree object from temporary index
        tree_hash = _run_git_command(['write-tree'], path, index_env)
        
        # Step 3: Create commit object
        commit_cmd = ['commit-tree', tree_hash, '-m', 'side commit for state capture']
        
        # Add parent if we have a current HEAD
        try:
            current_head = _run_git_command(['rev-parse', 'HEAD'], path)
            commit_cmd.extend(['-p', current_head])
        except RuntimeError:
            # No commits yet, no parent
            pass
        
        # Create the commit
        commit_hash = _run_git_command(commit_cmd, path)
        
        # Step 4: Create branch pointing to the commit
        _run_git_command(['branch', branch_name, commit_hash], path)
        
        return commit_hash
        
    finally:
        # Always cleanup temporary index
        _cleanup_temporary_index(temp_index_path)