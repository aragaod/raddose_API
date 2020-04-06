#!/usr/bin/bash
cd /dls/science/groups/i04/Python/applications/autodose/
uvicorn main:app --reload --host 0.0.0.0
