"""Allow ``python -m differentiater old.py new.py``."""

import sys

from differentiater.cli import main

sys.exit(main())
