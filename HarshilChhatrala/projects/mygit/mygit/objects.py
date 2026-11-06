import hashlib
from pathlib import Path
import zlib

GIT_DIR = Path(".mygit")


def init_repository():
    """Initializes the .mygit directory structure."""
    if GIT_DIR.exists():
        print("Reinitialized existing MyGit repository")
        return
    
    (GIT_DIR / "objects").mkdir(parents=True, exist_ok=True)
    (GIT_DIR / "refs" / "heads").mkdir(parents=True, exist_ok=True)
    
    # Point HEAD to the default main branch
    with open(GIT_DIR / "HEAD", "w") as f:
        f.write("ref: refs/heads/main\n")
    
    print(f"Initialized empty MyGit repository in {GIT_DIR.resolve()}")


def write_object(obj_type: str, data: bytes) -> str:
    """Writes a content-addressable object to the object store."""
    # Format: <type> <size>\0<content>
    header = f"{obj_type} {len(data)}".encode() + b"\x00"
    full_content = header + data
    
    # Calculate SHA-1 hash
    sha1 = hashlib.sha1(full_content).hexdigest()
    
    # Determine storage path: .mygit/objects/xx/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    obj_dir = GIT_DIR / "objects" / sha1[:2]
    obj_path = obj_dir / sha1[2:]
    
    if not obj_path.exists():
        obj_dir.mkdir(parents=True, exist_ok=True)
        # Compress using zlib
        compressed = zlib.compress(full_content)
        with open(obj_path, "wb") as f:
            f.write(compressed)
            
    return sha1


def read_object(sha1: str) -> tuple[str, bytes]:
    """Reads and decompresses an object from the object store, returning (type, content)."""
    obj_path = GIT_DIR / "objects" / sha1[:2] / sha1[2:]
    if not obj_path.exists():
        raise FileNotFoundError(f"Object {sha1} not found.")
        
    with open(obj_path, "rb") as f:
        compressed = f.read()
        
    full_content = zlib.decompress(compressed)
    
    # Split header and content at the null byte
    header, content = full_content.split(b"\x00", 1)
    obj_type, _ = header.decode().split(" ")
    
    return obj_type, content


def build_tree_from_index(index_data: dict) -> str:
    """Parses flat index paths into a nested tree structure and writes tree objects."""
    # Step 1: Build a nested dictionary structure from the flat paths
    # e.g., {'file_a.txt': 'sha1', 'docs': {'notes.txt': 'sha1'}}
    root = {}
    for path_str, sha1 in index_data.items():
        parts = Path(path_str).parts
        current = root
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = sha1

    def write_tree_recursive(tree_dict: dict) -> str:
        """Helper to recursively write tree objects from the nested dictionary."""
        entries = []
        
        for name, value in sorted(tree_dict.items()):
            if isinstance(value, dict):
                # It's a subdirectory, process its child tree first
                sub_tree_sha1 = write_tree_recursive(value)
                # mode 040000 for directory
                entries.append(f"040000 tree {sub_tree_sha1}\t{name}\n")
            else:
                # It's a file blob
                # mode 100644 for normal file
                entries.append(f"100644 blob {value}\t{name}\n")
                
        # Combine all entry lines into a single bytes payload
        tree_content = "".join(entries).encode()
        return write_object("tree", tree_content)

    return write_tree_recursive(root)


def read_tree_recursive(tree_sha1: str, base_path: str = "") -> dict:
    """Recursively parses a tree object back into a flat dict of path -> sha1."""
    if not tree_sha1:
        return {}
    
    obj_type, content = read_object(tree_sha1)
    if obj_type != "tree":
        raise ValueError(f"Object {tree_sha1} is not a tree.")
        
    entries = {}
    lines = content.decode().strip().split("\n") if content.strip() else []
    
    for line in lines:
        if not line:
            continue
        # Format: <mode> <type> <sha1>\t<name>
        meta, name = line.split("\t", 1)
        _, obj_type, sha1 = meta.split(" ")
        
        full_path = f"{base_path}/{name}" if base_path else name
        
        if obj_type == "tree":
            # Recurse down into directories
            entries.update(read_tree_recursive(sha1, full_path))
        else:
            entries[full_path] = sha1
            
    return entries