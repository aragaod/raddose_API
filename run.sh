#!/usr/bin/bash
cd /dls/science/groups/mx/Python/applications/raddoseAPI
/dls/science/groups/b21/PYTHON3/bin/uvicorn main:app --reload --host 0.0.0.0
