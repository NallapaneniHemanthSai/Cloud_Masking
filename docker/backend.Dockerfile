# Backend image — PLACEHOLDER (Milestone 2 scaffold).
# The functional image is authored in Milestone 17 (Docker). Pinned to Python 3.11 per ADR-0004.
# GDAL/rasterio system dependencies (Risk R-12) are handled explicitly in the M17 version.

FROM python:3.11-slim

# Placeholder only — real build steps (system GDAL, deps, app copy, uvicorn entrypoint) added in M17.
WORKDIR /app

# NOTE: Do NOT build this image at Milestone 2. It intentionally does not install dependencies yet.
CMD ["python", "-c", "print('Cloud Masking backend image is a Milestone 2 placeholder; built in M17.')"]
