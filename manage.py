#!/usr/bin/env python
"""Django's command-line utility for administrative tasks — DEV mode."""
import os
import sys


def main():
    # Dev branch uses settings_dev (SQLite, DEBUG=True)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ishemalink.settings_dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Make sure it's installed:\n"
            "  pip install -r requirements_dev.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
