"""Marks ``tests`` as a package so tests can import shared helpers.

With this file present, test modules can use absolute imports like
``from tests.helpers.cli import captured_stdout`` regardless of how
pytest is invoked.
"""
