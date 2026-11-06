import argparse

from mygit.commands import (
    cmd_add,
    cmd_branch,
    cmd_cat_file,
    cmd_checkout,
    cmd_commit,
    cmd_diff,
    cmd_hash_object,
    cmd_init,
    cmd_log,
    cmd_status,
    cmd_write_tree,
)


def main():
    parser = argparse.ArgumentParser(description="MyGit - A mini Git clone for learning internals.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    subparsers.add_parser("init", help="Initialize a new, empty MyGit repository")

    # hash-object
    hash_parser = subparsers.add_parser("hash-object", help="Compute object ID and optionally creates a blob from a file")
    hash_parser.add_argument("file", help="Path to the file to hash")
    hash_parser.add_argument("-w", action="store_true", help="Write the object into the object database")

    # cat-file
    cat_parser = subparsers.add_parser("cat-file", help="Provide content or type and size information for repository objects")
    cat_parser.add_argument("-p", action="store_true", required=True, help="Pretty-print the contents of <object> based on its type")
    cat_parser.add_argument("object", help="The SHA-1 hash of the object")

    # add
    add_parser = subparsers.add_parser("add", help="Add file contents to the staging index")
    add_parser.add_argument("files", nargs="+", help="Files or directories to stage")

    # write-tree
    subparsers.add_parser("write-tree", help="Create a tree object from the current index")

    # commit
    commit_parser = subparsers.add_parser("commit", help="Record staging index changes to the repository history")
    commit_parser.add_argument("-m", required=True, dest="message", help="Commit message logging changes")

    # log
    subparsers.add_parser("log", help="Show commit history logs")

    # status
    subparsers.add_parser("status", help="Show the working tree status")

    # checkout
    checkout_parser = subparsers.add_parser("checkout", help="Switch branches or restore working tree files")
    checkout_parser.add_argument("target", help="The branch name or commit hash to switch to")

    # branch
    branch_parser = subparsers.add_parser("branch", help="List or create branches")
    branch_parser.add_argument("name", nargs="?", help="Name of the branch to create")

    # diff
    subparsers.add_parser("diff", help="Show changes between commits, commit and working tree, etc")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init()
    elif args.command == "hash-object":
        cmd_hash_object(args.file, write=args.w)
    elif args.command == "cat-file":
        cmd_cat_file(args.object, pretty=args.p)
    elif args.command == "add":
        cmd_add(args.files)
    elif args.command == "write-tree":
        cmd_write_tree()
    elif args.command == "commit":
        cmd_commit(args.message)
    elif args.command == "log":
        cmd_log()
    elif args.command == "status":
        cmd_status()
    elif args.command == "checkout":
        cmd_checkout(args.target)
    elif args.command == "branch":
        cmd_branch(args.name)
    elif args.command == "diff":
        cmd_diff()


if __name__ == "__main__":
    main()