from pathlib import Path

GIT_DIR = Path(".mygit")


def get_current_branch_path() -> tuple[str, Path | None]:
    """Parses HEAD to find the current active branch name and its file path."""
    head_path = GIT_DIR / "HEAD"
    if not head_path.exists():
        return "HEAD detached", None
        
    with open(head_path, "r") as f:
        content = f.read().strip()
        
    if content.startswith("ref:"):
        ref_path_str = content.split(" ", 1)[1].strip()
        # BUGFIX: previously returned only the last path segment
        # (e.g. "feature/foo" became "foo"), which broke the "*" marker
        # in `branch` and any nested-branch comparisons. Return the full
        # branch name relative to refs/heads/ instead.
        prefix = "refs/heads/"
        branch_name = ref_path_str[len(prefix):] if ref_path_str.startswith(prefix) else ref_path_str
        return branch_name, GIT_DIR / ref_path_str
    else:
        # Detached HEAD state (contains raw SHA-1)
        return "DETACHED", None


def get_head_commit() -> str | None:
    """Gets the current commit hash that HEAD points to."""
    branch_name, branch_path = get_current_branch_path()
    if branch_path and branch_path.exists():
        with open(branch_path, "r") as f:
            return f.read().strip()
    elif not branch_path:
        # Detached HEAD, check raw hash directly in HEAD file
        with open(GIT_DIR / "HEAD", "r") as f:
            content = f.read().strip()
            if not content.startswith("ref:"):
                return content
    return None


def update_branch_ref(commit_sha1: str):
    """Updates the active branch ref file to point to the new commit hash."""
    branch_name, branch_path = get_current_branch_path()
    if branch_path:
        branch_path.parent.mkdir(parents=True, exist_ok=True)
        with open(branch_path, "w") as f:
            f.write(f"{commit_sha1}\n")
    else:
        # If detached, update HEAD directly
        with open(GIT_DIR / "HEAD", "w") as f:
            f.write(f"{commit_sha1}\n")