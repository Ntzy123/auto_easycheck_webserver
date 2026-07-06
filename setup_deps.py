"""Clone missing dependency repos (cross-platform, no shell-specific syntax)."""
import os
import subprocess
import sys

REPOS = [
    ("auto_easycheck", "https://github.com/Ntzy123/auto_easycheck.git"),
    ("easycheck_manager", "https://github.com/Ntzy123/easycheck_manager.git"),
    ("get-easycheck-url", "https://github.com/Ntzy123/get-easycheck-url.git"),
]

GIT_ENV = {**os.environ, "GIT_HTTP_LOW_SPEED_TIME": "30", "GIT_HTTP_LOW_SPEED_LIMIT": "1"}


def main() -> None:
    for name, url in REPOS:
        target = os.path.join("..", name)
        if os.path.isdir(target):
            print(f"  ✅ {name} 已存在，跳过克隆")
            continue
        print(f"  ⏳ 正在克隆 {name} ...")
        result = subprocess.run(
            ["git", "clone", url, target],
            capture_output=True, text=True,
            env=GIT_ENV,
        )
        if result.returncode != 0:
            print(f"  ❌ 克隆 {name} 失败: {result.stderr.strip()}", file=sys.stderr)
            sys.exit(1)
        print(f"  ✅ {name} 克隆完成")


if __name__ == "__main__":
    main()
