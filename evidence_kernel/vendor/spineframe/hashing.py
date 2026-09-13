"""Extracted unchanged compute_root_hash from SpineFrame artifacts.py.
Modified module: imports and surrounding functions omitted. See ORIGIN.json.
"""
import hashlib

def compute_root_hash(provenance_hashes: list[str]) -> str:
    """Compute root hash over all evidence provenance hashes.

    SHA-256 of sorted provenance_hashes joined by |.
    """
    canonical = "|".join(sorted(provenance_hashes))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


