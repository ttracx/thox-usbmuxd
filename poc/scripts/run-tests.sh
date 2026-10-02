#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
cd "$(dirname "$0")/../.."
PYTHONPATH=poc/host python3 -m unittest discover -s poc/tests -v
