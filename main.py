#!/usr/bin/env python3
"""
PyGit - A Git clone implementation in Python
Complete version control system with local repository support
"""

import os
import sys
import json
import hashlib
import shutil
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import difflib
import subprocess
from colorama import init, Fore, Style
init(autoreset=True)

# Configuration and Constants
PYGIT_DIR = ".pygit"
OBJECTS_DIR = "objects"
REFS_DIR = "refs"
HEADS_DIR = "heads"
INDEX_FILE = "index"
HEAD_FILE = "HEAD"
CONFIG_FILE = "config"

@dataclass
class FileEntry:
    """Represents a file entry in the index"""
    path: str
    hash: str
    mode: str
    size: int
    mtime: float

@dataclass
class CommitObject:
    """Represents a commit object"""
    tree: str
    parent: Optional[str]
    author: str
    committer: str
    timestamp: float
    message: str
    hash: Optional[str] = None

@dataclass
class TreeEntry:
    """Represents an entry in a tree object"""
    mode: str
    name: str
    hash: str
    type: str  # 'blob' or 'tree'

class PyGitError(Exception):
    """Custom exception for PyGit operations"""
    pass

class ObjectStore:
    """Handles storage and retrieval of Git objects"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.objects_path = self.repo_path / PYGIT_DIR / OBJECTS_DIR
        
    def _get_object_path(self, hash_str: str) -> Path:
        """Get the file path for an object hash"""
        return self.objects_path / hash_str[:2] / hash_str[2:]
    
    def store_object(self, content: bytes, obj_type: str) -> str:
        """Store an object and return its hash"""
        header = f"{obj_type} {len(content)}\0".encode()
        full_content = header + content
        hash_str = hashlib.sha1(full_content).hexdigest()
        
        obj_path = self._get_object_path(hash_str)
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(obj_path, 'wb') as f:
            f.write(full_content)
            
        return hash_str
    
    def get_object(self, hash_str: str) -> Tuple[str, bytes]:
        """Retrieve an object by hash"""
        obj_path = self._get_object_path(hash_str)
        
        if not obj_path.exists():
            raise PyGitError(f"Object {hash_str} not found")
            
        with open(obj_path, 'rb') as f:
            content = f.read()
            
        null_index = content.find(b'\0')
        if null_index == -1:
            raise PyGitError(f"Invalid object format for {hash_str}")
            
        header = content[:null_index].decode()
        obj_content = content[null_index + 1:]
        
        obj_type = header.split()[0]
        return obj_type, obj_content

class Index:
    """Manages the staging area (index)"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.index_path = self.repo_path / PYGIT_DIR / INDEX_FILE
        self.entries: Dict[str, FileEntry] = {}
        self.load()
        
    def load(self):
        """Load index from file"""
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r') as f:
                    data = json.load(f)
                    self.entries = {
                        path: FileEntry(**entry_data)
                        for path, entry_data in data.items()
                    }
            except (json.JSONDecodeError, KeyError):
                self.entries = {}
    
    def save(self):
        """Save index to file"""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, 'w') as f:
            json.dump(
                {path: asdict(entry) for path, entry in self.entries.items()},
                f, indent=2
            )
    
    def add_file(self, file_path: str, hash_str: str):
        """Add a file to the index"""
        full_path = self.repo_path / file_path
        if not full_path.exists():
            raise PyGitError(f"File {file_path} does not exist")
            
        stat = full_path.stat()
        self.entries[file_path] = FileEntry(
            path=file_path,
            hash=hash_str,
            mode=oct(stat.st_mode)[-3:],
            size=stat.st_size,
            mtime=stat.st_mtime
        )
        self.save()
    
    def remove_file(self, file_path: str):
        """Remove a file from the index"""
        if file_path in self.entries:
            del self.entries[file_path]
            self.save()
    
    def get_staged_files(self) -> Dict[str, FileEntry]:
        """Get all staged files"""
        return self.entries.copy()

class Repository:
    """Main repository class handling all Git operations"""
    
    def __init__(self, path: str = "."):
        self.path = Path(path).resolve()
        self.pygit_path = self.path / PYGIT_DIR
        self.object_store = ObjectStore(str(self.path))
        self.index = Index(str(self.path))
        
    def is_repository(self) -> bool:
        """Check if current directory is a PyGit repository"""
        return self.pygit_path.exists() and self.pygit_path.is_dir()
    
    def init(self) -> str:
        """Initialize a new repository"""
        if self.is_repository():
            return f"Repository already exists at {self.path}"
            
        # Create directory structure
        dirs_to_create = [
            self.pygit_path,
            self.pygit_path / OBJECTS_DIR,
            self.pygit_path / REFS_DIR,
            self.pygit_path / REFS_DIR / HEADS_DIR,
        ]
        
        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        # Create HEAD file pointing to main branch
        head_file = self.pygit_path / HEAD_FILE
        with open(head_file, 'w') as f:
            f.write("ref: refs/heads/main\n")
            
        # Create config file
        config_file = self.pygit_path / CONFIG_FILE
        with open(config_file, 'w') as f:
            json.dump({
                "user": {
                    "name": "PyGit User",
                    "email": "user@pygit.local"
                }
            }, f, indent=2)
            
        return f"Initialized empty PyGit repository in {self.pygit_path}"
    
    def add(self, file_paths: List[str]) -> str:
        """Add files to staging area"""
        if not self.is_repository():
            raise PyGitError("Not a PyGit repository")
            
        added_files = []
        
        for file_path in file_paths:
            if file_path == ".":
                # Add all files in current directory
                for root, dirs, files in os.walk(self.path):
                    # Skip .pygit directory
                    if PYGIT_DIR in dirs:
                        dirs.remove(PYGIT_DIR)
                    
                    for file in files:
                        full_path = Path(root) / file
                        rel_path = full_path.relative_to(self.path)
                        self._add_single_file(str(rel_path))
                        added_files.append(str(rel_path))
            else:
                self._add_single_file(file_path)
                added_files.append(file_path)
                
        return f"Added {len(added_files)} file(s) to staging area"
    
    def _add_single_file(self, file_path: str):
        """Add a single file to staging area"""
        full_path = self.path / file_path
        
        if not full_path.exists():
            raise PyGitError(f"File {file_path} does not exist")
            
        if full_path.is_dir():
            return  # Skip directories for now
            
        # Read file content and store as blob
        with open(full_path, 'rb') as f:
            content = f.read()
            
        hash_str = self.object_store.store_object(content, 'blob')
        self.index.add_file(file_path, hash_str)
    
    def status(self) -> str:
        """Show repository status"""
        if not self.is_repository():
            raise PyGitError("Not a PyGit repository")
            
        staged_files = self.index.get_staged_files()
        
        # Get current branch
        branch = self._get_current_branch()
        
        # Check for unstaged changes
        modified_files = []
        untracked_files = []
        
        # Walk through working directory
        for root, dirs, files in os.walk(self.path):
            if PYGIT_DIR in dirs:
                dirs.remove(PYGIT_DIR)
                
            for file in files:
                full_path = Path(root) / file
                rel_path = str(full_path.relative_to(self.path))
                
                if rel_path in staged_files:
                    # Check if file has been modified since staging
                    with open(full_path, 'rb') as f:
                        content = f.read()
                    current_hash = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
                    
                    if current_hash != staged_files[rel_path].hash:
                        modified_files.append(rel_path)
                else:
                    untracked_files.append(rel_path)
        
        # Build status message
        status_msg = f"On branch {branch}\n\n"
        
        if staged_files:
            status_msg += "Changes to be committed:\n"
            for file_path in staged_files:
                status_msg += f"  new file:   {file_path}\n"
            status_msg += "\n"
        
        if modified_files:
            status_msg += "Changes not staged for commit:\n"
            for file_path in modified_files:
                status_msg += f"  modified:   {file_path}\n"
            status_msg += "\n"
        
        if untracked_files:
            status_msg += "Untracked files:\n"
            for file_path in untracked_files:
                status_msg += f"  {file_path}\n"
            status_msg += "\n"
        
        if not staged_files and not modified_files and not untracked_files:
            status_msg += "nothing to commit, working tree clean\n"
            
        return status_msg.strip()
    
    def commit(self, message: str) -> str:
        """Create a new commit"""
        if not self.is_repository():
            raise PyGitError("Not a PyGit repository")
            
        staged_files = self.index.get_staged_files()
        if not staged_files:
            raise PyGitError("No changes added to commit")
            
        # Create tree object
        tree_hash = self._create_tree(staged_files)
        
        # Get parent commit
        parent_hash = self._get_head_commit()
        
        # Get user info
        config = self._load_config()
        author = f"{config['user']['name']} <{config['user']['email']}>"
        
        # Create commit object
        commit = CommitObject(
            tree=tree_hash,
            parent=parent_hash,
            author=author,
            committer=author,
            timestamp=time.time(),
            message=message
        )
        
        # Serialize and store commit
        commit_content = self._serialize_commit(commit)
        commit_hash = self.object_store.store_object(commit_content, 'commit')
        
        # Update HEAD
        self._update_head(commit_hash)
        
        return f"[{self._get_current_branch()} {commit_hash[:7]}] {message}"
    
    def log(self, limit: int = 10) -> str:
        """Show commit history"""
        if not self.is_repository():
            raise PyGitError("Not a PyGit repository")
            
        commit_hash = self._get_head_commit()
        if not commit_hash:
            return "No commits yet"
            
        logs = []
        count = 0
        
        while commit_hash and count < limit:
            commit = self._load_commit(commit_hash)
            
            log_entry = f"commit {commit_hash}\n"
            log_entry += f"Author: {commit.author}\n"
            log_entry += f"Date: {datetime.fromtimestamp(commit.timestamp).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            log_entry += f"    {commit.message}\n"
            
            logs.append(log_entry)
            commit_hash = commit.parent
            count += 1
            
        return "\n".join(logs)
    
    def diff(self, file_path: str = None) -> str:
        """Show differences between working directory and staged files"""
        if not self.is_repository():
            raise PyGitError("Not a PyGit repository")
            
        staged_files = self.index.get_staged_files()
        diffs = []
        
        files_to_check = [file_path] if file_path else None
        
        if not files_to_check:
            # Check all files in working directory
            files_to_check = []
            for root, dirs, files in os.walk(self.path):
                if PYGIT_DIR in dirs:
                    dirs.remove(PYGIT_DIR)
                for file in files:
                    full_path = Path(root) / file
                    rel_path = str(full_path.relative_to(self.path))
                    files_to_check.append(rel_path)
        
        for rel_path in files_to_check:
            full_path = self.path / rel_path
            
            if not full_path.exists():
                continue
                
            # Read current file content
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    current_lines = f.readlines()
            except UnicodeDecodeError:
                continue  # Skip binary files
                
            if rel_path in staged_files:
                # Get staged content
                obj_type, staged_content = self.object_store.get_object(staged_files[rel_path].hash)
                try:
                    staged_lines = staged_content.decode('utf-8').splitlines(keepends=True)
                except UnicodeDecodeError:
                    continue  # Skip binary files
                    
                # Generate diff
                diff = difflib.unified_diff(
                    staged_lines,
                    current_lines,
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}",
                    lineterm=''
                )
                
                diff_text = ''.join(diff)
                if diff_text:
                    diffs.append(diff_text)
        
        return '\n'.join(diffs) if diffs else "No differences found"
    
    def branch(self, branch_name: str = None, list_branches: bool = False) -> str:
        """Create or list branches"""
        if not self.is_repository():
            raise PyGitError("Not a PyGit repository")
            
        if list_branches or branch_name is None:
            return self._list_branches()
        
        # Create new branch
        current_commit = self._get_head_commit()
        if not current_commit:
            raise PyGitError("Cannot create branch with no commits")
            
        branch_path = self.pygit_path / REFS_DIR / HEADS_DIR / branch_name
        
        if branch_path.exists():
            raise PyGitError(f"Branch {branch_name} already exists")
            
        with open(branch_path, 'w') as f:
            f.write(current_commit + '\n')
            
        return f"Created branch {branch_name}"
    
    def checkout(self, branch_name: str) -> str:
        """Switch to a different branch"""
        if not self.is_repository():
            raise PyGitError("Not a PyGit repository")
            
        branch_path = self.pygit_path / REFS_DIR / HEADS_DIR / branch_name
        
        if not branch_path.exists():
            raise PyGitError(f"Branch {branch_name} does not exist")
            
        # Update HEAD to point to the branch
        head_path = self.pygit_path / HEAD_FILE
        with open(head_path, 'w') as f:
            f.write(f"ref: refs/heads/{branch_name}\n")
            
        return f"Switched to branch '{branch_name}'"
    
    # Helper methods
    def _get_current_branch(self) -> str:
        """Get the current branch name"""
        head_path = self.pygit_path / HEAD_FILE
        if not head_path.exists():
            return "main"
            
        with open(head_path, 'r') as f:
            content = f.read().strip()
            
        if content.startswith("ref: refs/heads/"):
            return content[16:]  # Remove "ref: refs/heads/"
        
        return "HEAD"  # Detached HEAD
    
    def _get_head_commit(self) -> Optional[str]:
        """Get the hash of the HEAD commit"""
        head_path = self.pygit_path / HEAD_FILE
        if not head_path.exists():
            return None
            
        with open(head_path, 'r') as f:
            content = f.read().strip()
            
        if content.startswith("ref: refs/heads/"):
            branch_name = content[16:]
            branch_path = self.pygit_path / REFS_DIR / HEADS_DIR / branch_name
            
            if not branch_path.exists():
                return None
                
            with open(branch_path, 'r') as f:
                return f.read().strip()
        else:
            return content  # Direct hash
    
    def _update_head(self, commit_hash: str):
        """Update HEAD to point to a new commit"""
        head_path = self.pygit_path / HEAD_FILE
        
        with open(head_path, 'r') as f:
            content = f.read().strip()
            
        if content.startswith("ref: refs/heads/"):
            branch_name = content[16:]
            branch_path = self.pygit_path / REFS_DIR / HEADS_DIR / branch_name
            
            with open(branch_path, 'w') as f:
                f.write(commit_hash + '\n')
        else:
            # Detached HEAD
            with open(head_path, 'w') as f:
                f.write(commit_hash + '\n')
    
    def _create_tree(self, staged_files: Dict[str, FileEntry]) -> str:
        """Create a tree object from staged files"""
        tree_entries = []
        
        for file_path, entry in staged_files.items():
            tree_entries.append(TreeEntry(
                mode=entry.mode,
                name=os.path.basename(file_path),
                hash=entry.hash,
                type='blob'
            ))
        
        # Sort entries by name
        tree_entries.sort(key=lambda x: x.name)
        
        # Serialize tree
        tree_content = ""
        for entry in tree_entries:
            tree_content += f"{entry.mode} {entry.name}\0{entry.hash}\n"
            
        return self.object_store.store_object(tree_content.encode(), 'tree')
    
    def _serialize_commit(self, commit: CommitObject) -> bytes:
        """Serialize a commit object"""
        content = f"tree {commit.tree}\n"
        
        if commit.parent:
            content += f"parent {commit.parent}\n"
            
        content += f"author {commit.author} {int(commit.timestamp)} +0000\n"
        content += f"committer {commit.committer} {int(commit.timestamp)} +0000\n"
        content += f"\n{commit.message}\n"
        
        return content.encode()
    
    def _load_commit(self, commit_hash: str) -> CommitObject:
        """Load a commit object from hash"""
        obj_type, content = self.object_store.get_object(commit_hash)
        
        if obj_type != 'commit':
            raise PyGitError(f"Object {commit_hash} is not a commit")
            
        lines = content.decode().split('\n')
        
        tree = None
        parent = None
        author = None
        committer = None
        timestamp = None
        message_lines = []
        
        in_message = False
        
        for line in lines:
            if not in_message:
                if line.startswith('tree '):
                    tree = line[5:]
                elif line.startswith('parent '):
                    parent = line[7:]
                elif line.startswith('author '):
                    parts = line[7:].rsplit(' ', 2)
                    author = parts[0]
                    timestamp = float(parts[1])
                elif line.startswith('committer '):
                    parts = line[10:].rsplit(' ', 2)
                    committer = parts[0]
                elif line == '':
                    in_message = True
            else:
                message_lines.append(line)
        
        message = '\n'.join(message_lines).strip()
        
        return CommitObject(
            tree=tree,
            parent=parent,
            author=author,
            committer=committer,
            timestamp=timestamp,
            message=message,
            hash=commit_hash
        )
    
    def _load_config(self) -> dict:
        """Load repository configuration"""
        config_path = self.pygit_path / CONFIG_FILE
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        
        return {
            "user": {
                "name": "PyGit User",
                "email": "user@pygit.local"
            }
        }
    
    def _list_branches(self) -> str:
        """List all branches"""
        heads_dir = self.pygit_path / REFS_DIR / HEADS_DIR
        
        if not heads_dir.exists():
            return "No branches found"
            
        branches = []
        current_branch = self._get_current_branch()
        
        for branch_file in heads_dir.iterdir():
            if branch_file.is_file():
                branch_name = branch_file.name
                prefix = "* " if branch_name == current_branch else "  "
                branches.append(f"{prefix}{branch_name}")
        
        return '\n'.join(sorted(branches))

class PyGitCLI:
    """Command-line interface for PyGit"""
    
    def __init__(self):
        self.repo = Repository()
        
    def run(self):
        """Run the CLI"""
        parser = argparse.ArgumentParser(description='PyGit - A Git clone in Python')
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Init command
        init_parser = subparsers.add_parser('init', help='Initialize a new repository')
        
        # Add command
        add_parser = subparsers.add_parser('add', help='Add files to staging area')
        add_parser.add_argument('files', nargs='+', help='Files to add')
        
        # Status command
        status_parser = subparsers.add_parser('status', help='Show repository status')
        
        # Commit command
        commit_parser = subparsers.add_parser('commit', help='Create a new commit')
        commit_parser.add_argument('-m', '--message', required=True, help='Commit message')
        
        # Log command
        log_parser = subparsers.add_parser('log', help='Show commit history')
        log_parser.add_argument('-n', '--number', type=int, default=10, help='Number of commits to show')
        
        # Diff command
        diff_parser = subparsers.add_parser('diff', help='Show differences')
        diff_parser.add_argument('file', nargs='?', help='Specific file to diff')
        
        # Branch command
        branch_parser = subparsers.add_parser('branch', help='List or create branches')
        branch_parser.add_argument('name', nargs='?', help='Branch name to create')
        branch_parser.add_argument('-a', '--all', action='store_true', help='List all branches')
        
        # Checkout command
        checkout_parser = subparsers.add_parser('checkout', help='Switch branches')
        checkout_parser.add_argument('branch', help='Branch name to switch to')
        
        if len(sys.argv) == 1:
            parser.print_help()
            return
            
        args = parser.parse_args()
        
        try:
            if args.command == 'init':
                print(self.repo.init())
                
            elif args.command == 'add':
                print(self.repo.add(args.files))
                
            elif args.command == 'status':
                print(self.repo.status())
                
            elif args.command == 'commit':
                print(self.repo.commit(args.message))
                
            elif args.command == 'log':
                print(self.repo.log(args.number))
                
            elif args.command == 'diff':
                print(self.repo.diff(args.file))
                
            elif args.command == 'branch':
                if args.name:
                    print(self.repo.branch(args.name))
                else:
                    print(self.repo.branch(list_branches=True))
                    
            elif args.command == 'checkout':
                print(self.repo.checkout(args.branch))
                
        except PyGitError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            sys.exit(1)

def print_logo():
    # Slant-style ASCII art
    logo = [
        "      ____                    _______ __",
        "     / __ \\__  __            / ____(_) /_",
        "    / /_/ / / / /  ______   / / __/ / __/",
        "   / ____/ /_/ /  /_____/  / /_/ / / /_",
        "  /_/    \\__, /            \\____/_/\\__/,",
        "        /____/"
    ]
    logo_width = max(len(line) for line in logo)
    term_width = 80
    pad = (term_width - logo_width) // 2
    for i, line in enumerate(logo):
        if i < 2:
            # 'Py' part (first two lines) in green
            print(' ' * pad + Fore.GREEN + Style.BRIGHT + line + Style.RESET_ALL)
        elif i == 2:
            # Middle line (dash) in yellow
            print(' ' * pad + Fore.YELLOW + Style.BRIGHT + line + Style.RESET_ALL)
        else:
            # 'Git' part (last three lines) in red/orange
            print(' ' * pad + Fore.RED + Style.BRIGHT + line + Style.RESET_ALL)
    # Center the colored text below the logo
    py = Fore.GREEN + Style.BRIGHT + 'Py' + Style.RESET_ALL
    dash = Fore.YELLOW + Style.BRIGHT + ' - ' + Style.RESET_ALL
    git = Fore.RED + Style.BRIGHT + 'Git' + Style.RESET_ALL
    text = py + dash + git
    print(' ' * (pad + (logo_width - len('Py - Git')) // 2) + text + '\n')

def main():
    """Main entry point"""
    print_logo()  # Show logo at start
    cli = PyGitCLI()
    cli.run()

if __name__ == "__main__":
    main()