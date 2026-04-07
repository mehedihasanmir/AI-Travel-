from pathlib import Path
import sys

# Allow running with both:
# 1) python app/main.py api
# 2) python -m app.main api
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.server import run_cli_or_server


def main() -> None:
    run_cli_or_server()


if __name__ == "__main__":
    main()
