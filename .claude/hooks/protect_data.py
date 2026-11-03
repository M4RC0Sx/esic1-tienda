"""PreToolUse hook: keep the data/ folder read-only.

Reads the hook payload from stdin. Denies file-writing tools that target
data/ and Bash commands that look like they modify anything inside data/.
Reads (cat, ls, grep, python scripts that only read) are always allowed.
"""

import json
import os
import re
import sys
from pathlib import Path


PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()
DATA_DIR = PROJECT_DIR / "data"

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
# Commands whose arguments are modified, so any data/ argument is a violation.
MUTATORS = {
    "rm", "rmdir", "mv", "touch", "mkdir", "chmod", "chown", "chgrp",
    "truncate", "ln", "unlink", "shred", "tee", "install", "rsync",
    "patch", "chflags", "xattr", "mkfifo",
}
DATA_REF = re.compile(
    r"""(?:^|[\s'"=:(<>])(?:\./)?(?:%s/)?data(?:/|(?=[\s'"):;|&<>]|$))"""
    % re.escape(str(PROJECT_DIR).lstrip("/"))
)


def deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def is_in_data(raw_path: str) -> bool:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = PROJECT_DIR / path
    resolved = Path(os.path.realpath(path))
    return resolved == DATA_DIR or DATA_DIR in resolved.parents


def refs_data(text: str) -> bool:
    absolute = str(DATA_DIR)
    return absolute in text or bool(DATA_REF.search(text))


def segment_modifies_data(segment: str) -> bool:
    if not refs_data(segment):
        return False
    # Output redirection into data/ (>, >>, >|, &>)
    if re.search(r"(?:>>?\||>>?|&>)\s*['\"]?\S*data(?:/|\b)", segment):
        return True
    words = segment.split()
    # Skip env assignments and common wrappers to find the real command.
    while words and (re.match(r"\w+=", words[0]) or words[0] in {"sudo", "command", "env", "time", "nohup"}):
        words = words[1:]
    if not words:
        return False
    cmd = os.path.basename(words[0])
    if cmd in MUTATORS:
        return True
    if cmd == "cp":
        args = [w for w in words[1:] if not w.startswith("-")]
        return bool(args) and refs_data(args[-1])
    if cmd in {"sed", "perl", "ruby"} and any(re.fullmatch(r"-\w*i\w*", w) or w.startswith("-i") for w in words[1:]):
        return True
    if cmd == "dd" and any(w.startswith("of=") and refs_data(w[3:]) for w in words):
        return True
    if cmd == "git" and len(words) > 1 and words[1] in {"checkout", "restore", "clean", "rm", "mv", "reset", "stash"}:
        return True
    return False


def main() -> None:
    payload = json.load(sys.stdin)
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    if tool in WRITE_TOOLS:
        target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if target and is_in_data(target):
            deny(f"data/ is read-only: {tool} on {target} is blocked.")
    elif tool == "Bash":
        command = tool_input.get("command", "")
        for segment in re.split(r"&&|\|\||;|\||\n", command):
            if segment_modifies_data(segment):
                deny(
                    "data/ is read-only: this Bash command would modify it "
                    f"({segment.strip()[:120]!r})."
                )


if __name__ == "__main__":
    main()
