"""
Entry point for: python3 -m attack <command> [options]
Delegates to attack.cli.main().
"""

import sys
from attack.cli import main

if __name__ == "__main__":
    sys.exit(main())
