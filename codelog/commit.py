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

All functions raise RuntimeError if not in a git repository or if git commands fail.
'''

import subprocess
from typing import Optional


def _run_git_command(args: list[str], path: Optional[str] = None) -> str:
    '''Runs a git command and returns the output.
    
    Args:
        args: List of command arguments (e.g., ['rev-parse', 'HEAD'])
        path: Optional path to run the git command in. If None, uses current directory.
        
    Returns:
        str: The command output (stripped of whitespace)
        
    Raises:
        RuntimeError: If the git command fails or if not in a git repository.
    '''
    try:
        cmd = ['git'] + args
        if path:
            cmd = ['git', '-C', path] + args
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git command failed: {e.stderr}") from e


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
