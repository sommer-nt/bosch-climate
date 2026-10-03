# Macht das Paket `splitklima` für pytest importierbar.

import os

# Tests laden keine Klimadaten aus dem Netz (BWP-Klimakarte) – siehe tests/test_klima_plz.py
os.environ.setdefault("KLIMADATEN_AUTO", "0")
