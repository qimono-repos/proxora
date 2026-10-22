"""Allow ``python -m proxora`` to run the command-line entry point."""

import sys

from proxora import main

if __name__ == "__main__":
    sys.exit(main())
