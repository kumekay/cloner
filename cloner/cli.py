import sys

from .core import clone_or_cd

SHELL_FUNCTION = """
clone() {
    if [ "$1" = "--init" ]; then
        command clone --init
        return
    fi
    local dir
    dir=$(command clone "$@")
    if [ $? -eq 0 ] && [ -d "$dir" ]; then
        cd "$dir" || return
    fi
}
"""


def main():
    if len(sys.argv) < 2:
        print("Usage: clone <git-url>", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "--init":
        print(SHELL_FUNCTION.strip())
        sys.exit(0)

    url = sys.argv[1]

    try:
        path = clone_or_cd(url)
        print(path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
