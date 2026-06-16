"""Clone missing dependency repos (cross-platform, no shell-specific syntax)."""
import os
import subprocess
import sys

REPOS = [
    ("auto_easycheck", "https://github.com/Ntzy123/auto_easycheck.git"),
    ("easycheck_manager", "https://github.com/Ntzy123/easycheck_manager.git"),
]

GIT_ENV = {**os.environ, "GIT_HTTP_LOW_SPEED_TIME": "30", "GIT_HTTP_LOW_SPEED_LIMIT": "1"}


def main() -> None:
    for name, url in REPOS:
        target = os.path.join("..", name)
        if os.path.isdir(target):
            print(f"{name} 已存在")
            continue
        print(f"Cloning {name}...")
        result = subprocess.run(
            ["git", "clone", url, target],
            env=GIT_ENV,
        )
        if result.returncode != 0:
            print(f"ERROR: {name} 克隆失败，请检查网络连接", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
