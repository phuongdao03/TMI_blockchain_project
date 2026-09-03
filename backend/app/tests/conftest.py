"""Keep the test process isolated from developer and production environment files."""

from __future__ import annotations

import os

# Application modules construct worker settings while pytest collects tests. Set a
# coherent local chain before those imports so a developer's Polygon `.env` cannot
# make the suite fail during collection. Individual configuration tests may still
# override these values explicitly.
os.environ["BLOCKCHAIN_NETWORK"] = "local"
os.environ["BLOCKCHAIN_CHAIN_ID"] = "31337"
