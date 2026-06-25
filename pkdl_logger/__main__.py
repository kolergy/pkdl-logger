"""Allow ``python -m pkdl_logger`` to run the CLI."""

import sys

from pkdl_logger.cli import main

if __name__ == "__main__":
    sys.exit(main())
