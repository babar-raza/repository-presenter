"""Support ``python -m repository_presenter`` with the same behavior as the console script."""

import sys

from repository_presenter.cli import main

if __name__ == "__main__":
    sys.exit(main())
