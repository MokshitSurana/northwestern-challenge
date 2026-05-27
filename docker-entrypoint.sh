#!/bin/sh
set -e

echo "FairGuard ETL Pipeline"
echo "DATA_ROOT=$DATA_ROOT"
echo "OUTPUT_ROOT=$OUTPUT_ROOT"

if [ "$SAMPLE" = "1" ]; then
    echo "Running in SAMPLE mode (fast validation)"
    uv run scripts/01_build_index.py --sample
else
    echo "Running FULL build (~2.5 hours)"
    uv run scripts/01_build_index.py
fi

echo ""
echo "Running revolving door scan..."
uv run scripts/02_revolving_door_scan.py

echo ""
echo "Running agency concentration scan..."
uv run scripts/03_agency_concentration.py

echo ""
echo "Done. Outputs in $OUTPUT_ROOT"
