"""Smoke test: every module in src/ can be imported."""

import importlib

import pytest

MODULES = [
    "data",
    "render",
    "ocr_check",
    "encode",
    "score",
    "experiments",
    "mitigate",
    "metrics",
    "figures",
]


@pytest.mark.parametrize("name", MODULES)
def test_import(name):
    importlib.import_module(f"src.{name}")
