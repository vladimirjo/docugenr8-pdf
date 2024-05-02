#!/bin/bash

ruff check
ruff format
mypy src/
pytest --cov=docugenr8_pdf tests/
