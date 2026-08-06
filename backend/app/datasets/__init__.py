"""Dataset layer.

Milestone 3 (dataset management) adds provenance/integrity/download helpers:

* :mod:`app.datasets.manifest` — load & validate the provenance manifest (``datasets.yaml``).
* :mod:`app.datasets.integrity` — checksums and file/directory existence checks.
* :mod:`app.datasets.download` — resumable, dependency-free file downloader.

Dataset **loaders** for training (CloudSEN12 primary, On Cloud N reference benchmark), preprocessing,
and spatial-block splits are added in Milestone 4 — not here. No preprocessing/ML logic at Milestone 3.
"""
