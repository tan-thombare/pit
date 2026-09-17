"""Desktop application entry point."""

import logging
import sys

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pit")


def main() -> None:
    """Launch the Prompt Injection Tester desktop application."""
    try:
        from pit.ui.app import launch_app
        launch_app()
    except ImportError as exc:
        print(f"Failed to launch GUI: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
