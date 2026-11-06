from datetime import datetime
import difflib
import hashlib
from pathlib import Path
import sys
import time

from .index import read_index, write_index
from .objects import (
    build_tree_from_index,
    init_repository,
    read_object,
    read_tree_recursive,
    write_object,
)
from .refs import get_current_branch_path, get_head_commit, update_branch_ref


def cmd_add(files: list[str]):
    index = read_index()
    
    for file_str in files:
        path = Path(file_str)
        if not path.exists():
            print(f"fatal: pathspec '{file_str}' did not match any files")
            continue
            
        # If it's a directory, walk through it and add all files
        if path.is_dir():
            for subpath in path.rglob("*"):
                # FIX: Ignore __pycache__ directories
                if subpath.is_file() and ".mygit" not in subpath.parts and "__pycache__" not in subpath.parts:
                    # Keep paths relative to the working directory root
                    rel_path = str(subpath.relative_to(Path(".")))
                    with open(subpath, "rb") as f:
                        sha1 = write_object("blob", f.read())
                    index[rel_path] = sha1
        else:
            rel_path = str(path.relative_to(Path(".")))
            with open(path, "rb") as f:
                sha1 = write_object("blob", f.read())
            index[rel_path] = sha1
            
    write_index(index)
    print(f"Staged {len(files)} path(s).")


def cmd_init():
    init_repository()


def cmd_hash_object(file_path: str, write: bool = True):
    path = Path(file_path)
    if not path.exists():
        print(f"fatal: Cannot open '{file_path}': No such file", file=sys.stderr)
        sys.exit(1)
        
    with open(path, "rb") as f:
        data = f.read()
        
    if write:
        sha1 = write_object("blob", data)
    else:
        # Just compute the hash without writing
        header = f"blob {len(data)}".encode() + b"\x00"
        sha1 = hashlib.sha1(header + data).hexdigest()
        
    print(sha1)


def cmd_cat_file(sha1: str, pretty: bool):
    if not pretty:
        print("fatal: Only -p (pretty print) is currently supported", file=sys.stderr)
        sys.exit(1)
        
    try:
        obj_type, content = read_object(sha1)
        if obj_type in ("blob", "commit"):
            # Blobs and commits can be printed directly as text
            sys.stdout.buffer.write(content)
        elif obj_type == "tree":
            # For now, print tree contents as raw text string (until we implement trees)
            sys.stdout.buffer.write(content)
    except FileNotFoundError:
        print(f"fatal: Not a valid object name {sha1}", file=sys.stderr)
        sys.exit(1)


def cmd_write_tree():
    index = read_index()
    if not index:
        print("fatal: Nothing staged to write a tree from.")
        return
        
    root_tree_sha1 = build_tree_from_index(index)
    print(root_tree_sha1)


def cmd_commit(message: str):
    index = read_index()
    if not index:
        print("nothing to commit (create/copy files and use \"mygit add\" to stage)")
        return

    # 1. Generate the root tree snapshot
    tree_sha1 = build_tree_from_index(index)
    
    # 2. Get parent commit hash
    parent_sha1 = get_head_commit()
    
    # 3. Assemble commit body metadata
    commit_lines = [f"tree {tree_sha1}"]
    if parent_sha1:
        commit_lines.append(f"parent {parent_sha1}")
        
    # Standard author metadata with timestamp
    timestamp = int(time.time())
    # Format: Name <email> timestamp timezone_offset
    commit_lines.append(f"author MyGit User <user@mygit.internal> {timestamp} +0000")
    commit_lines.append(f"committer MyGit User <user@mygit.internal> {timestamp} +0000")
    commit_lines.append("") # Empty line boundary before message
    commit_lines.append(message)
    
    commit_content = "\n".join(commit_lines).encode()
    
    # 4. Write object to database and move branch reference forward
    commit_sha1 = write_object("commit", commit_content)
    update_branch_ref(commit_sha1)
    
    branch_name, _ = get_current_branch_path()
    print(f"[{branch_name} {commit_sha1[:7]}] {message}")


def cmd_log():
    commit_sha1 = get_head_commit()
    if not commit_sha1:
        print("fatal: your current branch 'main' does not have any commits yet")
        return

    while commit_sha1:
        try:
            obj_type, content = read_object(commit_sha1)
        except FileNotFoundError:
            print(f"fatal: commit object {commit_sha1} is missing")
            break

        if obj_type != "commit":
            print(f"fatal: object {commit_sha1} is not a commit")
            break

        lines = content.decode().split("\n")
        
        # Parse the commit lines
        metadata = {}
        message_lines = []
        is_message = False

        for line in lines:
            if is_message:
                message_lines.append(line)
            elif line == "":
                is_message = True
            else:
                key, val = line.split(" ", 1)
                metadata[key] = val

        # Extract timestamp out of author line: "Name <email> 1783929462 +0000"
        author_info = metadata.get("author", "Unknown")
        date_str = ""
        if " " in author_info:
            parts = author_info.split(" ")
            # The second to last part is our unix timestamp
            try:
                timestamp = int(parts[-2])
                date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, IndexError):
                pass

        # Print the classic Git log block
        print(f"\033[33mcommit {commit_sha1}\033[0m") # Yellow text for hash
        print(f"Author: {author_info.split(' <')[0]}")
        if date_str:
            print(f"Date:   {date_str}")
        print("\n    " + "\n    ".join(message_lines).strip() + "\n")

        # Move back in time to the parent commit
        commit_sha1 = metadata.get("parent")


def cmd_status():
    index = read_index()
    
    # 1. Gather files from HEAD commit
    head_sha1 = get_head_commit()
    head_files = {}
    if head_sha1:
        # Read commit object to get its root tree hash
        _, commit_content = read_object(head_sha1)
        for line in commit_content.decode().split("\n"):
            if line.startswith("tree "):
                tree_sha1 = line.split(" ")[1]
                head_files = read_tree_recursive(tree_sha1)
                break

    # 2. Gather files from actual Working Directory on disk
    wd_files = {}
    for p in Path(".").rglob("*"):
        # FIX: Ignore __pycache__ directories from appearing in untracked files
        if p.is_file() and ".mygit" not in p.parts and "__pycache__" not in p.parts:
            # Match standard relative pathing strings
            rel_path = str(p.relative_to(Path(".")))
            wd_files[rel_path] = p

    # 3. Process differences
    staged = []    # Changes staged for commit
    unstaged = []  # Changes not staged for commit
    untracked = [] # Untracked files

    # Staged: Compare HEAD vs Index
    all_staged_keys = set(head_files.keys()).union(index.keys())
    for path in sorted(all_staged_keys):
        if path not in head_files and path in index:
            staged.append(f"new file:   {path}")
        elif path in head_files and path not in index:
            staged.append(f"deleted:    {path}")
        elif head_files[path] != index[path]:
            staged.append(f"modified:   {path}")

    # Unstaged & Untracked: Compare Index vs Working Directory
    for path in sorted(wd_files.keys()):
        file_path = wd_files[path]
        
        # Calculate current on-disk raw hash to compare with index
        with open(file_path, "rb") as f:
            data = f.read()
        header = f"blob {len(data)}".encode() + b"\x00"
        wd_sha1 = hashlib.sha1(header + data).hexdigest()
        
        if path not in index:
            untracked.append(path)
        elif index[path] != wd_sha1:
            unstaged.append(f"modified:   {path}")

    # Detect deleted files from index that still exist in index but not on disk
    for path in index.keys():
        if path not in wd_files:
            unstaged.append(f"deleted:    {path}")

    # 4. Print ANSI formatted report status layout
    # FIX: Dynamically read the actual active branch instead of hardcoding "main"
    branch_name, _ = get_current_branch_path()
    print(f"On branch {branch_name}\n")
    
    if staged:
        print("Changes to be committed:")
        for line in staged:
            print(f"  \033[32m{line}\033[0m") # Green text
        print()
        
    if unstaged:
        print("Changes not staged for commit:")
        for line in unstaged:
            print(f"  \033[31m{line}\033[0m") # Red text
        print()
        
    if untracked:
        print("Untracked files:")
        for line in untracked:
            print(f"  \033[31m  {line}\033[0m") # Red text
        print()
        
    if not staged and not unstaged and not untracked:
        print("nothing to commit, working tree clean")


def cmd_checkout(target: str):
    # 1. Resolve target identifier (check if it's a branch or a raw commit hash)
    branch_ref_path = Path(".mygit/refs/heads") / target
    
    if branch_ref_path.exists():
        with open(branch_ref_path, "r") as f:
            commit_sha1 = f.read().strip()
        is_branch = True
    else:
        # Check if target is a valid commit object hash directly
        try:
            obj_type, _ = read_object(target)
            if obj_type != "commit":
                print(f"fatal: reference is not a commit: {target}")
                return
            commit_sha1 = target
            is_branch = False
        except FileNotFoundError:
            print(f"error: pathspec '{target}' did not match any file(s) known to mygit")
            return

    # 2. Extract the target tree from the commit object
    _, commit_content = read_object(commit_sha1)
    target_tree_sha1 = None
    for line in commit_content.decode().split("\n"):
        if line.startswith("tree "):
            target_tree_sha1 = line.split(" ")[1]
            break
            
    if not target_tree_sha1:
        print("fatal: corrupted commit object (missing tree pointer)")
        return

    target_files = read_tree_recursive(target_tree_sha1)

    # =========================================================================
    # NEW SAFETY CHECK: Prevent overwriting/deleting uncommitted local changes
    # =========================================================================
    index = read_index()
    for rel_path, index_sha1 in index.items():
        p = Path(rel_path)
        if p.exists():
            # Calculate current on-disk raw hash to see if the user modified it
            with open(p, "rb") as f:
                data = f.read()
            header = f"blob {len(data)}".encode() + b"\x00"
            wd_sha1 = hashlib.sha1(header + data).hexdigest()
            
            # If the working directory doesn't match the index, the file has uncommitted changes!
            if wd_sha1 != index_sha1:
                print(f"error: Your local changes to the following files would be overwritten by checkout:\n  {rel_path}")
                print("Please commit your changes or stash them before you switch branches.")
                return
    # =========================================================================

    # 3. Clean working directory of currently tracked files in the staging index
    for rel_path in index.keys():
        p = Path(rel_path)
        if p.exists():
            p.unlink()
            # Clean up parent directories if they are left empty
            for parent in p.parents:
                if parent != Path(".") and parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()

    # 4. Write new files into working directory from object blobs
    for rel_path, sha1 in target_files.items():
        _, file_content = read_object(sha1)
        p = Path(rel_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            f.write(file_content)

    # 5. Reset staging index to match this snapshot exactly
    write_index(target_files)

    # 6. Move HEAD pointer
    with open(".mygit/HEAD", "w") as f:
        if is_branch:
            f.write(f"ref: refs/heads/{target}\n")
            print(f"Switched to branch '{target}'")
        else:
            f.write(f"{commit_sha1}\n")
            print(f"Note: switching to '{target}'. You are in 'detached HEAD' state.")


def cmd_branch(name: str = None):
    heads_dir = Path(".mygit/refs/heads")
    
    # If no name is provided, list all existing branches
    if not name:
        current_branch, _ = get_current_branch_path()
        for branch_file in heads_dir.iterdir():
            if branch_file.is_file():
                prefix = "* " if branch_file.name == current_branch else "  "
                print(f"{prefix}{branch_file.name}")
        return

    # Otherwise, create a new branch pointing to the current HEAD commit
    head_commit = get_head_commit()
    if not head_commit:
        print("fatal: Not a valid object name: 'main'. Cannot create branch from empty history.")
        return

    new_branch_path = heads_dir / name
    if new_branch_path.exists():
        print(f"fatal: A branch named '{name}' already exists.")
        return

    with open(new_branch_path, "w") as f:
        f.write(f"{head_commit}\n")
    print(f"Branch '{name}' created pointing to {head_commit[:7]}")


def cmd_diff():
    index = read_index()
    
    if not index:
        print("No files staged or tracked to diff against.")
        return

    has_diff = False

    for rel_path, sha1 in index.items():
        p = Path(rel_path)
        if not p.exists():
            # File was deleted on disk but is still in the index
            print(f"\033[31mdeleted: {rel_path}\033[0m")
            has_diff = True
            continue

        # 1. Read the version stored in the index (blob)
        _, blob_content = read_object(sha1)
        index_lines = blob_content.decode(encoding="utf-8", errors="replace").splitlines(keepends=True)

        # 2. Read the current version on disk
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            disk_lines = f.readlines()

        # 3. Generate a unified diff comparison
        diff = list(difflib.unified_diff(
            index_lines, 
            disk_lines, 
            fromfile=f"a/{rel_path}", 
            tofile=f"b/{rel_path}"
        ))

        if diff:
            has_diff = True
            print(f"diff --mygit a/{rel_path} b/{rel_path}")
            for line in diff:
                if line.startswith("+") and not line.startswith("+++"):
                    print(f"\033[32m{line.rstrip()}\033[0m") # Green for additions
                elif line.startswith("-") and not line.startswith("---"):
                    print(f"\033[31m{line.rstrip()}\033[0m") # Red for removals
                else:
                    print(line.rstrip())
            print()

    if not has_diff:
        print("No changes between index and working directory.")