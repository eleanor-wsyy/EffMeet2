"""Unified local bench compatibility entrypoint. Run one process per database."""
from services.controller.app import create_app

app = create_app(bench=True)
