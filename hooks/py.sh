#!/bin/sh
# Run a Shipwright hook with whichever Python 3.9+ this system has (python3 on macOS/Linux, often python or py
# on Windows). The check rejects Windows' Store placeholder. With no Python the hook is skipped, never an error.
for p in python3 python py; do
  if "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
    exec "$p" "$@"
  fi
done
exit 0
