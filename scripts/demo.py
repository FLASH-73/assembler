"""Start the AURA demo stack (mock mode — no hardware required).

Usage:
    python scripts/demo.py

Starts the FastAPI backend on port 8000 with stub primitives.
Open a second terminal and run: cd frontend && npm run dev
"""

import logging
import os
import sys
from pathlib import Path

# Ensure the project root is on PYTHONPATH so uvicorn's reloader subprocess
# can find the nextis package.
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, PROJECT_ROOT)
os.environ["PYTHONPATH"] = PROJECT_ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")

import uvicorn  # noqa: E402

BANNER = """
╔══════════════════════════════════════╗
║  AURA — Assembly Platform            ║
║  API:      http://localhost:8000      ║
║  Frontend: http://localhost:3000      ║
║  Mode:     Mock (no hardware)         ║
╚══════════════════════════════════════╝
"""


def main() -> None:
    """Start the AURA backend in mock demo mode."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("aura.demo")

    print(BANNER)
    logger.info("Starting AURA backend (mock mode)")
    logger.info("Frontend: cd frontend && npm run dev")

    uvicorn.run(
        "nextis.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
