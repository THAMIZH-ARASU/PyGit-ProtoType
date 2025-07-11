# PyGit

<p align="center">
  <pre>
        <span style="color: #00ff00; font-weight: bold;">      ____                    _______ __
             / __ \__  __            / ____(_) /_
            / /_/ / / / /  ______   / / __/ / __/
           / ____/ /_/ /  /_____/  / /_/ / / /_
          /_/    \__, /            \____/_/\__/,</span>
<span style="color: #ffcc00; font-weight: bold;">                /____/</span>
  </pre>
  <h2>Py <span style="color: #ffcc00;">-</span> <span style="color: #ff6600;">Git</span></h2>
</p>

A Python implementation of a Git-like version control system, featuring a colorful ASCII logo and essential version control commands. PyGit is designed for learning, experimentation, and small projects.

---

## Features
- Initialize a new repository (`init`)
- Add files to the staging area (`add`)
- View repository status (`status`)
- Commit changes (`commit`)
- View commit history (`log`)
- Show file differences (`diff`)
- Create and list branches (`branch`)
- Switch branches (`checkout`)
- Colorful, centered ASCII logo on startup

## Requirements
- Python 3.7+
- [colorama](https://pypi.org/project/colorama/) (for colored terminal output)

Install dependencies:
```bash
pip install colorama
```

## Installation
Clone the repository:
```bash
git clone https://github.com/yourusername/PyGit.git
cd PyGit
```

## Usage
Run the CLI:
```bash
python main.py --help
```

Example output:
```
      ____                    _______ __
     / __ \__  __            / ____(_) /_
    / /_/ / / / /  ______   / / __/ / __/
   / ____/ /_/ /  /_____/  / /_/ / / /_
  /_/    \__, /            \____/_/\__/,        
        /____/

                            Py - Git

usage: main.py [-h] {init,add,status,commit,log,diff,branch,checkout} ...

PyGit - A Git clone in Python

positional arguments:
  {init,add,status,commit,log,diff,branch,checkout}
                        Available commands
    init                Initialize a new repository
    add                 Add files to staging area
    status              Show repository status
    commit              Create a new commit
    log                 Show commit history
    diff                Show differences
    branch              List or create branches
    checkout            Switch branches

options:
  -h, --help            show this help message and exit
```

### Common Commands
- Initialize a repo:
  ```bash
  python main.py init
  ```
- Add files:
  ```bash
  python main.py add file.txt
  ```
- Commit changes:
  ```bash
  python main.py commit -m "Initial commit"
  ```
- View status:
  ```bash
  python main.py status
  ```
- View log:
  ```bash
  python main.py log
  ```
- Diff:
  ```bash
  python main.py diff
  ```
- Branch:
  ```bash
  python main.py branch new-feature
  python main.py branch --all
  ```
- Checkout:
  ```bash
  python main.py checkout new-feature
  ```

## Contributing
Contributions are welcome! Please open issues or submit pull requests for improvements or bug fixes.

## License
This project is licensed under the MIT License. 