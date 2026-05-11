"""Marks ``code_files`` as importable when running tests locally.

Inside the Foundry Code Interpreter sandbox, the files in this folder are
uploaded as flat agent files and imported by name (no package), which is
why the modules use top-level relative imports like ``from docx_text``
instead of ``from .docx_text``.
"""
