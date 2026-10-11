#!/bin/zsh
# Arranca el Estudio de video y abre el panel en http://localhost:8765
cd "${0:A:h}"
export PYTHONPATH="$PWD"
( sleep 2 && open http://localhost:8765 ) &
exec .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8765
