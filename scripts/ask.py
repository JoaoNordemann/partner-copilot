#!/usr/bin/env python
"""Shortcut for partner-copilot ask without reinstalling the console entry point."""

import sys

from partner_copilot.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["ask", *sys.argv[1:]]))
