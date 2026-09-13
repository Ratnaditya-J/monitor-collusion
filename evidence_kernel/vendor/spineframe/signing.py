"""Pluggable cryptographic signing and verification for provenance bundles.

Supported algorithms:
  - **Ed25519** (default) — classical elliptic-curve signatures
  - **ML-DSA-65** (NIST FIPS 204, formerly Dilithium3) — post-quantum lattice signatures
  - **hybrid** — signs with BOTH Ed25519 and ML-DSA-65 (NIST-recommended transition)

Provides:
  - Key generation and loading
  - Sign provenance bundles and approval snapshots
  - Verify signatures (auto-detects algorithm from bundle)
  - CLI-compatible key management

Dependencies:
  - Ed25519: ``pip install spineframe[signing]``  (cryptography>=42.0)
  - ML-DSA-65: ``pip install spineframe[pqsigning]``  (pqcrypto>=0.4)
  - hybrid: both of the above

Key storage:
  Keys live in ``~/.spineframe/keys/`` by default.
  - Ed25519:  ``signing_key.pem`` / ``signing_key.pub`` (PEM format)
  - ML-DSA-65: ``signing_key_ml_dsa_65.key`` / ``signing_key_ml_dsa_65.pub`` (raw binary)

Bundle signature format::

    {
        "signature": "<hex-encoded signature>",
        "public_key": "<hex-encoded public key>",
        "signer": "<actor identity>",
        "signed_at": "<ISO 8601 timestamp>",
        "algorithm": "Ed25519" | "ML-DSA-65" | "hybrid",
        "signed_fields": ["run.run_id", "run.query", "root_hash", ...],
    }

Hybrid bundles contain a ``signatures`` list with one entry per algorithm.
"""

from __future__ import annotations

import abc
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Lazy imports — only fail if actually used without the dependency
# ---------------------------------------------------------------------------

_HAS_CRYPTOGRAPHY = False
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization

    _HAS_CRYPTOGRAPHY = True
except ImportError:
    pass

_HAS_PQCRYPTO = False
try:
    from pqcrypto.sign import ml_dsa_65 as _ml_dsa_65

    _HAS_PQCRYPTO = True
except ImportError:
    pass


def _require_cryptography() -> None:
    if not _HAS_CRYPTOGRAPHY:
        raise ImportError(
            "Ed25519 signing requires the 'cryptography' package. "
            "Install with: pip install spineframe[signing]"
        )


def _require_pqcrypto() -> None:
    if not _HAS_PQCRYPTO:
        raise ImportError(
            "ML-DSA-65 signing requires the 'pqcrypto' package. "
            "Install with: pip install spineframe[pqsigning]"
        )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALGORITHM_ED25519 = "Ed25519"
ALGORITHM_ML_DSA_65 = "ML-DSA-65"
ALGORITHM_HYBRID = "hybrid"

VALID_ALGORITHMS = {ALGORITHM_ED25519, ALGORITHM_ML_DSA_65, ALGORITHM_HYBRID}

DEFAULT_KEY_DIR = Path.home() / ".spineframe" / "keys"

# ML-DSA-65 key filenames (raw binary — no PEM wrapper exists for PQ keys)
_ML_DSA_65_PRIVATE_FILE = "signing_key_ml_dsa_65.key"
_ML_DSA_65_PUBLIC_FILE = "signing_key_ml_dsa_65.pub"


# ---------------------------------------------------------------------------
# Signing backend ABC
# ---------------------------------------------------------------------------


class SigningBackend(abc.ABC):
    """Abstract base class for signing backends."""

    @property
    @abc.abstractmethod
    def algorithm(self) -> str:
        """Return the algorithm identifier (e.g. 'Ed25519', 'ML-DSA-65')."""

    @abc.abstractmethod
    def generate_keypair(self, key_dir: Path) -> tuple[bytes, bytes]:
        """Generate a keypair and persist to *key_dir*.

        Returns (raw_private_bytes, raw_public_bytes).
        """

    @abc.abstractmethod
    def load_private_key(self, key_dir: Path) -> Any:
        """Load the private key object from *key_dir*."""

    @abc.abstractmethod
    def load_public_key_bytes(self, key_dir: Path) -> bytes:
        """Load the raw public key bytes from *key_dir*."""

    @abc.abstractmethod
    def sign(self, private_key: Any, message: bytes) -> bytes:
        """Produce a signature over *message*."""

    @abc.abstractmethod
    def verify(self, public_key_bytes: bytes, message: bytes, signature: bytes) -> bool:
        """Return True if *signature* is valid for *message* and *public_key_bytes*."""

    @abc.abstractmethod
    def public_key_hex(self, key_dir: Path) -> str:
        """Return hex-encoded public key."""


# ---------------------------------------------------------------------------
# Ed25519 backend
# ---------------------------------------------------------------------------


class Ed25519Backend(SigningBackend):
    """Ed25519 elliptic-curve signing backend (cryptography library)."""

    @property
    def algorithm(self) -> str:
        return ALGORITHM_ED25519

    def generate_keypair(self, key_dir: Path) -> tuple[bytes, bytes]:
        _require_cryptography()
        key_dir.mkdir(parents=True, exist_ok=True)

        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Write private key PEM
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        private_path = key_dir / "signing_key.pem"
        private_path.write_bytes(private_pem)
        private_path.chmod(0o600)

        # Write public key PEM
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        (key_dir / "signing_key.pub").write_bytes(public_pem)

        raw_private = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        raw_public = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return raw_private, raw_public

    def load_private_key(self, key_dir: Path) -> "Ed25519PrivateKey":
        _require_cryptography()
        pem_path = key_dir / "signing_key.pem"
        if not pem_path.exists():
            raise FileNotFoundError(
                f"No Ed25519 signing key found at {pem_path}. "
                f"Generate one with: spineframe keygen"
            )
        pem_data = pem_path.read_bytes()
        return serialization.load_pem_private_key(pem_data, password=None)  # type: ignore[return-value]

    def load_public_key_bytes(self, key_dir: Path) -> bytes:
        _require_cryptography()
        pem_path = key_dir / "signing_key.pub"
        if not pem_path.exists():
            raise FileNotFoundError(f"No Ed25519 public key found at {pem_path}.")
        pem_data = pem_path.read_bytes()
        public_key = serialization.load_pem_public_key(pem_data)
        return public_key.public_bytes(  # type: ignore[union-attr]
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def sign(self, private_key: Any, message: bytes) -> bytes:
        return private_key.sign(message)

    def verify(self, public_key_bytes: bytes, message: bytes, signature: bytes) -> bool:
        _require_cryptography()
        try:
            pub = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            pub.verify(signature, message)
            return True
        except Exception:
            return False

    def public_key_hex(self, key_dir: Path) -> str:
        return self.load_public_key_bytes(key_dir).hex()


# ---------------------------------------------------------------------------
# ML-DSA-65 backend
# ---------------------------------------------------------------------------


class MlDsa65Backend(SigningBackend):
    """ML-DSA-65 (FIPS 204 / Dilithium3) post-quantum signing backend.

    Uses the ``pqcrypto`` library which bundles the PQClean C reference
    implementation. Keys are stored as raw binary files since PEM encoding
    is not standardized for post-quantum keys.

    Installation::

        pip install pqcrypto>=0.4

    The pqcrypto wheel includes compiled C code — no separate system library
    installation is needed. Pre-built wheels are available for Linux (x86_64,
    aarch64) and macOS (x86_64, arm64).
    """

    @property
    def algorithm(self) -> str:
        return ALGORITHM_ML_DSA_65

    def generate_keypair(self, key_dir: Path) -> tuple[bytes, bytes]:
        _require_pqcrypto()
        key_dir.mkdir(parents=True, exist_ok=True)

        public_key, secret_key = _ml_dsa_65.generate_keypair()

        # Write raw binary keys
        private_path = key_dir / _ML_DSA_65_PRIVATE_FILE
        private_path.write_bytes(secret_key)
        private_path.chmod(0o600)

        (key_dir / _ML_DSA_65_PUBLIC_FILE).write_bytes(public_key)

        return bytes(secret_key), bytes(public_key)

    def load_private_key(self, key_dir: Path) -> bytes:
        _require_pqcrypto()
        path = key_dir / _ML_DSA_65_PRIVATE_FILE
        if not path.exists():
            raise FileNotFoundError(
                f"No ML-DSA-65 signing key found at {path}. "
                f"Generate one with: spineframe keygen --algorithm ml-dsa-65"
            )
        return path.read_bytes()

    def load_public_key_bytes(self, key_dir: Path) -> bytes:
        _require_pqcrypto()
        path = key_dir / _ML_DSA_65_PUBLIC_FILE
        if not path.exists():
            raise FileNotFoundError(f"No ML-DSA-65 public key found at {path}.")
        return path.read_bytes()

    def sign(self, private_key: Any, message: bytes) -> bytes:
        _require_pqcrypto()
        return _ml_dsa_65.sign(private_key, message)

    def verify(self, public_key_bytes: bytes, message: bytes, signature: bytes) -> bool:
        _require_pqcrypto()
        try:
            return _ml_dsa_65.verify(public_key_bytes, message, signature)
        except Exception:
            return False

    def public_key_hex(self, key_dir: Path) -> str:
        return self.load_public_key_bytes(key_dir).hex()


# ---------------------------------------------------------------------------
# Backend registry
# ---------------------------------------------------------------------------

_BACKENDS: dict[str, SigningBackend] = {}


def _get_backend(algorithm: str) -> SigningBackend:
    """Return the backend for *algorithm*, creating lazily."""
    alg = algorithm.lower().replace("_", "-")
    if alg in ("ed25519",):
        key = ALGORITHM_ED25519
        if key not in _BACKENDS:
            _BACKENDS[key] = Ed25519Backend()
        return _BACKENDS[key]
    elif alg in ("ml-dsa-65", "mldsa65", "dilithium", "dilithium3"):
        key = ALGORITHM_ML_DSA_65
        if key not in _BACKENDS:
            _BACKENDS[key] = MlDsa65Backend()
        return _BACKENDS[key]
    else:
        raise ValueError(
            f"Unknown signing algorithm: {algorithm!r}. "
            f"Valid options: ed25519, ml-dsa-65, hybrid"
        )


# ---------------------------------------------------------------------------
# Public API — key management
# ---------------------------------------------------------------------------


def generate_keypair(
    key_dir: Path | None = None,
    *,
    algorithm: str = "ed25519",
) -> tuple[bytes, bytes]:
    """Generate a signing keypair and save to disk.

    Args:
        key_dir: Directory to write key files. Defaults to ~/.spineframe/keys/.
        algorithm: ``"ed25519"`` (default), ``"ml-dsa-65"``, or ``"hybrid"``.

    Returns:
        (private_key_bytes, public_key_bytes) for single-algorithm modes.
        For hybrid mode, generates BOTH keypairs and returns the Ed25519 pair.
    """
    key_dir = key_dir or DEFAULT_KEY_DIR

    if algorithm.lower() == "hybrid":
        ed_backend = _get_backend("ed25519")
        pq_backend = _get_backend("ml-dsa-65")
        ed_priv, ed_pub = ed_backend.generate_keypair(key_dir)
        pq_backend.generate_keypair(key_dir)
        return ed_priv, ed_pub

    backend = _get_backend(algorithm)
    return backend.generate_keypair(key_dir)


def load_private_key(key_dir: Path | None = None, *, algorithm: str = "ed25519") -> Any:
    """Load a private key from disk.

    For Ed25519, returns an ``Ed25519PrivateKey`` object.
    For ML-DSA-65, returns raw secret key bytes.
    """
    key_dir = key_dir or DEFAULT_KEY_DIR
    backend = _get_backend(algorithm)
    return backend.load_private_key(key_dir)


def load_public_key(key_dir: Path | None = None, *, algorithm: str = "ed25519") -> Any:
    """Load the public key from disk.

    For Ed25519, returns an ``Ed25519PublicKey`` object (backward compat).
    For ML-DSA-65, returns raw public key bytes.
    """
    key_dir = key_dir or DEFAULT_KEY_DIR
    if algorithm.lower() in ("ed25519",):
        _require_cryptography()
        pem_path = key_dir / "signing_key.pub"
        if not pem_path.exists():
            raise FileNotFoundError(f"No public key found at {pem_path}.")
        pem_data = pem_path.read_bytes()
        return serialization.load_pem_public_key(pem_data)
    backend = _get_backend(algorithm)
    return backend.load_public_key_bytes(key_dir)


def public_key_hex(key_dir: Path | None = None, *, algorithm: str = "ed25519") -> str:
    """Return hex-encoded public key."""
    key_dir = key_dir or DEFAULT_KEY_DIR
    backend = _get_backend(algorithm)
    return backend.public_key_hex(key_dir)


# ---------------------------------------------------------------------------
# Canonical serialization
# ---------------------------------------------------------------------------


def _canonical_json(data: dict[str, Any]) -> bytes:
    """Produce deterministic JSON bytes for signing.

    Keys are sorted, no whitespace, UTF-8 encoded.
    """
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _extract_signable_fields(bundle: dict[str, Any]) -> dict[str, Any]:
    """Extract the fields from a provenance bundle that are signed.

    We sign a deterministic subset — not the entire bundle — so that
    adding non-critical metadata fields doesn't break verification.
    """
    run = bundle.get("run", {})
    return {
        "run_id": run.get("run_id", ""),
        "query": run.get("query", ""),
        "created_at": run.get("created_at", ""),
        "root_hash": bundle.get("root_hash", ""),
        "source_count": len(bundle.get("sources", [])),
        "chunk_count": len(bundle.get("chunks", [])),
        "claim_count": len(bundle.get("claims", [])),
        "evidence_count": len(bundle.get("evidence", [])),
    }


# ---------------------------------------------------------------------------
# Bundle signing
# ---------------------------------------------------------------------------


def _make_signature_block(
    backend: SigningBackend,
    message: bytes,
    signable: dict[str, Any],
    *,
    signer: str,
    key_dir: Path,
) -> dict[str, Any]:
    """Create a signature block using the given backend."""
    private_key = backend.load_private_key(key_dir)
    sig_bytes = backend.sign(private_key, message)
    pub_bytes = backend.load_public_key_bytes(key_dir)

    return {
        "signature": sig_bytes.hex(),
        "public_key": pub_bytes.hex(),
        "signer": signer,
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "algorithm": backend.algorithm,
        "signed_fields": sorted(signable.keys()),
    }


def sign_bundle(
    bundle: dict[str, Any],
    *,
    signer: str = "",
    key_dir: Path | None = None,
    algorithm: str = "ed25519",
) -> dict[str, Any]:
    """Sign a provenance bundle.

    Adds a ``signature`` block to the bundle dict and returns the
    modified bundle. Does NOT mutate the input.

    Args:
        bundle: Output of ``export_provenance_bundle()``.
        signer: Actor identity string (e.g. "alice@acme.com").
        key_dir: Key directory. Defaults to ~/.spineframe/keys/.
        algorithm: ``"ed25519"`` (default), ``"ml-dsa-65"``, or ``"hybrid"``.

    Returns:
        New dict with the bundle contents plus a ``signature`` block.
        For hybrid mode, the ``signature`` block has ``algorithm: "hybrid"``
        and a ``signatures`` list containing one entry per algorithm.
    """
    key_dir = key_dir or DEFAULT_KEY_DIR

    signable = _extract_signable_fields(bundle)
    message = _canonical_json(signable)

    signed = dict(bundle)

    alg = algorithm.lower().replace("_", "-")
    if alg == "hybrid":
        ed_backend = _get_backend("ed25519")
        pq_backend = _get_backend("ml-dsa-65")

        ed_sig = _make_signature_block(
            ed_backend, message, signable, signer=signer, key_dir=key_dir,
        )
        pq_sig = _make_signature_block(
            pq_backend, message, signable, signer=signer, key_dir=key_dir,
        )

        signed["signature"] = {
            "algorithm": ALGORITHM_HYBRID,
            "signer": signer,
            "signed_at": datetime.now(timezone.utc).isoformat(),
            "signed_fields": sorted(signable.keys()),
            "signatures": [ed_sig, pq_sig],
        }
    else:
        backend = _get_backend(algorithm)
        signed["signature"] = _make_signature_block(
            backend, message, signable, signer=signer, key_dir=key_dir,
        )

    return signed


def verify_bundle_signature(bundle: dict[str, Any]) -> dict[str, Any]:
    """Verify the signature on a signed provenance bundle.

    Auto-detects the algorithm from the signature block.

    Returns::

        {
            "valid": bool,
            "signer": str,
            "signed_at": str,
            "public_key": str,
            "algorithm": str,
            "error": str,  # empty if valid
        }
    """
    sig_block = bundle.get("signature")
    if not sig_block:
        return {
            "valid": False,
            "signer": "",
            "signed_at": "",
            "public_key": "",
            "algorithm": "",
            "error": "No signature block found in bundle",
        }

    algorithm = sig_block.get("algorithm", ALGORITHM_ED25519)

    if algorithm == ALGORITHM_HYBRID:
        return _verify_hybrid_bundle(bundle, sig_block)

    return _verify_single_algorithm_bundle(bundle, sig_block, algorithm)


def _verify_single_algorithm_bundle(
    bundle: dict[str, Any],
    sig_block: dict[str, Any],
    algorithm: str,
) -> dict[str, Any]:
    """Verify a single-algorithm signature block."""
    try:
        sig_hex = sig_block["signature"]
        pub_hex = sig_block["public_key"]
        sig_bytes = bytes.fromhex(sig_hex)
        pub_bytes = bytes.fromhex(pub_hex)
    except (KeyError, ValueError) as exc:
        return {
            "valid": False,
            "signer": sig_block.get("signer", ""),
            "signed_at": sig_block.get("signed_at", ""),
            "public_key": sig_block.get("public_key", ""),
            "algorithm": algorithm,
            "error": f"Malformed signature block: {exc}",
        }

    signable = _extract_signable_fields(bundle)
    message = _canonical_json(signable)

    try:
        backend = _get_backend(algorithm)
    except ValueError as exc:
        return {
            "valid": False,
            "signer": sig_block.get("signer", ""),
            "signed_at": sig_block.get("signed_at", ""),
            "public_key": pub_hex,
            "algorithm": algorithm,
            "error": str(exc),
        }

    valid = backend.verify(pub_bytes, message, sig_bytes)

    if not valid:
        return {
            "valid": False,
            "signer": sig_block.get("signer", ""),
            "signed_at": sig_block.get("signed_at", ""),
            "public_key": pub_hex,
            "algorithm": algorithm,
            "error": "Signature verification failed",
        }

    return {
        "valid": True,
        "signer": sig_block.get("signer", ""),
        "signed_at": sig_block.get("signed_at", ""),
        "public_key": pub_hex,
        "algorithm": algorithm,
        "error": "",
    }


def _verify_hybrid_bundle(
    bundle: dict[str, Any],
    sig_block: dict[str, Any],
) -> dict[str, Any]:
    """Verify a hybrid signature bundle — ALL constituent signatures must be valid."""
    signatures = sig_block.get("signatures", [])
    if not signatures:
        return {
            "valid": False,
            "signer": sig_block.get("signer", ""),
            "signed_at": sig_block.get("signed_at", ""),
            "public_key": "",
            "algorithm": ALGORITHM_HYBRID,
            "error": "Hybrid signature block has no constituent signatures",
        }

    results = []
    for sub_sig in signatures:
        sub_alg = sub_sig.get("algorithm", ALGORITHM_ED25519)
        result = _verify_single_algorithm_bundle(bundle, sub_sig, sub_alg)
        results.append(result)

    all_valid = all(r["valid"] for r in results)
    errors = [r["error"] for r in results if r["error"]]

    # Collect public keys from all sub-signatures
    pub_keys = [r.get("public_key", "") for r in results]

    return {
        "valid": all_valid,
        "signer": sig_block.get("signer", ""),
        "signed_at": sig_block.get("signed_at", ""),
        "public_key": pub_keys[0] if len(pub_keys) == 1 else ", ".join(pub_keys),
        "algorithm": ALGORITHM_HYBRID,
        "algorithms": [s.get("algorithm", "") for s in signatures],
        "sub_results": results,
        "error": "; ".join(errors) if errors else "",
    }


# ---------------------------------------------------------------------------
# Approval snapshot signing
# ---------------------------------------------------------------------------


def sign_approval(
    run_id: str,
    approved_at: str,
    approved_by: str,
    graph_hash: str,
    root_hash: str,
    *,
    key_dir: Path | None = None,
    algorithm: str = "ed25519",
) -> dict[str, Any]:
    """Sign an approval snapshot — stamps approval with cryptographic proof.

    Returns a signature block that can be stored in the run manifest or
    as a standalone artifact.
    """
    key_dir = key_dir or DEFAULT_KEY_DIR

    signable = {
        "run_id": run_id,
        "approved_at": approved_at,
        "approved_by": approved_by,
        "graph_hash": graph_hash,
        "root_hash": root_hash,
    }
    message = _canonical_json(signable)

    alg = algorithm.lower().replace("_", "-")
    if alg == "hybrid":
        ed_backend = _get_backend("ed25519")
        pq_backend = _get_backend("ml-dsa-65")

        ed_sig = _make_signature_block(
            ed_backend, message, signable, signer=approved_by, key_dir=key_dir,
        )
        ed_sig["signable_data"] = signable

        pq_sig = _make_signature_block(
            pq_backend, message, signable, signer=approved_by, key_dir=key_dir,
        )
        pq_sig["signable_data"] = signable

        return {
            "algorithm": ALGORITHM_HYBRID,
            "signer": approved_by,
            "signed_at": approved_at,
            "signed_fields": sorted(signable.keys()),
            "signable_data": signable,
            "signatures": [ed_sig, pq_sig],
        }

    backend = _get_backend(algorithm)
    block = _make_signature_block(
        backend, message, signable, signer=approved_by, key_dir=key_dir,
    )
    block["signable_data"] = signable
    return block


def verify_approval_signature(approval_sig: dict[str, Any]) -> dict[str, Any]:
    """Verify an approval signature. Auto-detects algorithm.

    Returns same format as verify_bundle_signature.
    """
    algorithm = approval_sig.get("algorithm", ALGORITHM_ED25519)

    if algorithm == ALGORITHM_HYBRID:
        return _verify_hybrid_approval(approval_sig)

    return _verify_single_approval(approval_sig, algorithm)


def _verify_single_approval(
    approval_sig: dict[str, Any],
    algorithm: str,
) -> dict[str, Any]:
    """Verify a single-algorithm approval signature."""
    try:
        sig_hex = approval_sig["signature"]
        pub_hex = approval_sig["public_key"]
        sig_bytes = bytes.fromhex(sig_hex)
        pub_bytes = bytes.fromhex(pub_hex)
        signable = approval_sig["signable_data"]
    except (KeyError, ValueError) as exc:
        return {
            "valid": False,
            "signer": approval_sig.get("signer", ""),
            "signed_at": approval_sig.get("signed_at", ""),
            "public_key": approval_sig.get("public_key", ""),
            "algorithm": algorithm,
            "error": f"Malformed approval signature: {exc}",
        }

    message = _canonical_json(signable)

    try:
        backend = _get_backend(algorithm)
    except ValueError as exc:
        return {
            "valid": False,
            "signer": approval_sig.get("signer", ""),
            "signed_at": approval_sig.get("signed_at", ""),
            "public_key": pub_hex,
            "algorithm": algorithm,
            "error": str(exc),
        }

    valid = backend.verify(pub_bytes, message, sig_bytes)

    if not valid:
        return {
            "valid": False,
            "signer": approval_sig.get("signer", ""),
            "signed_at": approval_sig.get("signed_at", ""),
            "public_key": pub_hex,
            "algorithm": algorithm,
            "error": "Approval signature verification failed",
        }

    return {
        "valid": True,
        "signer": approval_sig.get("signer", ""),
        "signed_at": approval_sig.get("signed_at", ""),
        "public_key": pub_hex,
        "algorithm": algorithm,
        "error": "",
    }


def _verify_hybrid_approval(approval_sig: dict[str, Any]) -> dict[str, Any]:
    """Verify a hybrid approval signature — ALL sub-signatures must be valid."""
    signatures = approval_sig.get("signatures", [])
    if not signatures:
        return {
            "valid": False,
            "signer": approval_sig.get("signer", ""),
            "signed_at": approval_sig.get("signed_at", ""),
            "public_key": "",
            "algorithm": ALGORITHM_HYBRID,
            "error": "Hybrid approval signature has no constituent signatures",
        }

    results = []
    for sub_sig in signatures:
        sub_alg = sub_sig.get("algorithm", ALGORITHM_ED25519)
        result = _verify_single_approval(sub_sig, sub_alg)
        results.append(result)

    all_valid = all(r["valid"] for r in results)
    errors = [r["error"] for r in results if r["error"]]

    return {
        "valid": all_valid,
        "signer": approval_sig.get("signer", ""),
        "signed_at": approval_sig.get("signed_at", ""),
        "public_key": "",
        "algorithm": ALGORITHM_HYBRID,
        "sub_results": results,
        "error": "; ".join(errors) if errors else "",
    }
