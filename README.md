# Codelog

A Python package for Git commit tracking utilities designed to ensure experiment reproducibility by verifying that code is properly tracked before running experiments.

## Overview

Codelog provides functions to:
- Get commit hashes for version tracking
- Verify that all code changes are committed before experiments
- Create side commits to capture current state without affecting your main branch
- Ensure reproducibility by maintaining a clear link between code state and experiment results

## Installation

### From GitHub

```bash
pip install git+https://github.com/acutkosky/codelog.git
```

### Development Setup

```bash
git clone https://github.com/acutkosky/codelog.git
cd codelog
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
pip install -e .
```

## Usage

### Basic Usage

```python
from codelog.commit import (
    get_most_recent_commit_hash,
    get_commit_hash,
    ensure_code_is_tracked,
    make_side_commit
)

# Get the most recent commit hash (regardless of working directory state)
commit_hash = get_most_recent_commit_hash()
print(f"Most recent commit: {commit_hash}")

# Get commit hash only if working directory is clean
clean_hash = get_commit_hash()
if clean_hash:
    print(f"Working directory is clean, commit: {clean_hash}")
else:
    print("Working directory has uncommitted changes")

# Ensure all changes are committed (raises error if not)
try:
    tracked_hash = ensure_code_is_tracked()
    print(f"Code is tracked, commit: {tracked_hash}")
except RuntimeError as e:
    print(f"Error: {e}")

# Create a side commit to capture current state
side_commit_hash = make_side_commit()
print(f"Side commit created: {side_commit_hash}")
```

### Experiment Reproducibility

```python
from codelog.commit import ensure_code_is_tracked
import mlflow

def run_experiment():
    # Ensure code is tracked before running experiment
    # Will throw an error if code is not committed.
    commit_hash = ensure_code_is_tracked()
    
    # Log the commit hash with your experiment
    mlflow.log_param("git_commit", commit_hash)
    
    # Run your experiment...
    results = train_model()
    
    # Log results
    mlflow.log_metrics(results)
    
    return results
```

### Working with Different Paths

```python
from codelog.commit import get_commit_hash

# Check a specific repository path
repo_path = "/path/to/your/repo"
commit_hash = get_commit_hash(path=repo_path)

# Check current directory
current_hash = get_commit_hash()  # path=None defaults to current directory
```

### Side Commits for State Capture

```python
from codelog.commit import make_side_commit

# Create a side commit to capture current state
# This doesn't affect your current branch but creates a recoverable state
side_hash = make_side_commit()

# Force creation of side commit even if working directory is clean
forced_side_hash = make_side_commit(force=True)

print(f"Current state captured at: {side_hash}")
```

## API Reference

### `get_most_recent_commit_hash(path: Optional[str] = None) -> str`

Returns the most recent commit hash of the codebase, regardless of working directory state.

**Parameters:**
- `path` (Optional[str]): Path to the git repository. If None, uses current directory.

**Returns:**
- `str`: The full commit hash of the most recent commit on the current branch.

**Raises:**
- `RuntimeError`: If not in a git repository or git command fails.

### `get_commit_hash(path: Optional[str] = None) -> Optional[str]`

Returns the current commit hash only if the working directory is clean (no unstaged changes, no untracked files).

**Parameters:**
- `path` (Optional[str]): Path to the git repository. If None, uses current directory.

**Returns:**
- `Optional[str]`: The current commit hash if working directory is clean, None if there are uncommitted changes.

**Raises:**
- `RuntimeError`: If not in a git repository or git command fails.

### `ensure_code_is_tracked(path: Optional[str] = None) -> str`

Ensures that the current code is checked in with git. Raises an error if there are uncommitted changes.

**Parameters:**
- `path` (Optional[str]): Path to the git repository. If None, uses current directory.

**Returns:**
- `str`: The commit hash of the codebase.

**Raises:**
- `RuntimeError`: If there are uncommitted changes or if not in a git repository.

### `make_side_commit(path: Optional[str] = None, force: bool = False) -> str`

Creates a side commit to capture the current state without affecting the current branch. The commit is created on a new branch with a unique name.

**Parameters:**
- `path` (Optional[str]): Path to the git repository. If None, uses current directory.
- `force` (bool): If True, always create a side commit even if working directory is clean. If False, return current commit hash if working directory is clean.

**Returns:**
- `str`: The commit hash of the side commit (or current commit if clean and not forced).

**Raises:**
- `RuntimeError`: If not in a git repository or git command fails.

## Error Handling

All functions raise `RuntimeError` with descriptive messages when:
- The current directory is not a git repository
- Git commands fail
- There are uncommitted changes (for `ensure_code_is_tracked`)

```python
try:
    commit_hash = ensure_code_is_tracked()
except RuntimeError as e:
    print(f"Error: {e}")
    # Handle the error appropriately
```


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
