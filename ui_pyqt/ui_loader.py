"""Helpers for loading the Qt Designer forms shipped with the application."""

from pathlib import Path

from PyQt6 import uic


UI_DIR = Path(__file__).with_name("forms")


def load_ui(form_name: str, instance) -> None:
    """Populate *instance* from a ``.ui`` file created by Qt Designer."""
    uic.loadUi(UI_DIR / form_name, instance)
