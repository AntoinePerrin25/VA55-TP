#!/bin/sh
cd "$(dirname "$0")/.."
exec tp_mqtt/.venv/bin/python tp_mqtt/simulate.py "$@"
