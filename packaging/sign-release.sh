#!/usr/bin/env bash
# Sign a release artifact with ML-DSA-65 (FIPS 204) via OpenSSL 3.5+.
#
#   packaging/sign-release.sh dist/proxora_0.1.0-1_amd64.deb [private-key.pem]
#
# Construction:
#   artifact.sha256      SHA-256 of the artifact (sha256sum format)
#   artifact.sha256.sig  ML-DSA-65 signature over artifact.sha256
#   artifact.sig.json    algorithm, digest and signer metadata
#
# The artifact is bound to the signature through the signed SHA-256 manifest.
# This also avoids OpenSSL's one-shot ML-DSA input limit for large files.
#
# The private key defaults to $PROXORA_SIGNING_KEY. It does not distribute the
# public key; see packaging/README.md.
set -euo pipefail

ARTIFACT=${1:?usage: sign-release.sh <artifact> [private-key.pem]}
KEY=${2:-${PROXORA_SIGNING_KEY:-}}
ALGORITHM=${PROXORA_SIGN_ALGORITHM:-ML-DSA-65}
SIGNER=${PROXORA_SIGNER:-Qimono}

[[ -f "$ARTIFACT" ]] || { echo "no such artifact: $ARTIFACT" >&2; exit 1; }
[[ -n "$KEY" ]] || { echo "set PROXORA_SIGNING_KEY or pass a private key" >&2; exit 1; }
[[ -f "$KEY" ]] || { echo "no such key: $KEY" >&2; exit 1; }

CHECKSUM=$ARTIFACT.sha256
SIGNATURE=$CHECKSUM.sig

( cd "$(dirname "$ARTIFACT")" && sha256sum "$(basename "$ARTIFACT")" ) > "$CHECKSUM"
openssl dgst -sign "$KEY" -out "$SIGNATURE" "$CHECKSUM"

DIGEST=$(cut -d' ' -f1 "$CHECKSUM")
cat > "$ARTIFACT.sig.json" <<EOF
{
  "artifact": "$(basename "$ARTIFACT")",
  "algorithm": "$ALGORITHM",
  "sha256": "$DIGEST",
  "checksum": "$(basename "$CHECKSUM")",
  "signature": "$(basename "$SIGNATURE")",
  "signer": "$SIGNER",
  "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

printf 'signed %s\n  algorithm: %s\n  sha256:    %s\n  signature: %s over %s\n' \
  "$ARTIFACT" "$ALGORITHM" "$DIGEST" "$SIGNATURE" "$CHECKSUM"
