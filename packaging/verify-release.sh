#!/usr/bin/env bash
# Verify an ML-DSA-65 release signature made by sign-release.sh.
#
#   packaging/verify-release.sh dist/proxora_0.1.0-1_amd64.deb release-public.pem
#
# Checks, in order:
#   1. the ML-DSA-65 signature over the SHA-256 manifest;
#   2. the artifact's actual SHA-256 against that signed manifest.
# Exits non-zero on a missing file, a bad signature, or a modified artifact.
#
# Trust in the public key is NOT established here: obtain the key through a
# channel you trust before relying on this result.
set -euo pipefail

ARTIFACT=${1:?usage: verify-release.sh <artifact> <public-key.pem>}
PUBKEY=${2:?usage: verify-release.sh <artifact> <public-key.pem>}

CHECKSUM=$ARTIFACT.sha256
SIGNATURE=$CHECKSUM.sig

[[ -f "$ARTIFACT" ]] || { echo "no such artifact: $ARTIFACT" >&2; exit 1; }
[[ -f "$CHECKSUM" ]] || { echo "missing checksum manifest: $CHECKSUM" >&2; exit 1; }
[[ -f "$SIGNATURE" ]] || { echo "missing signature: $SIGNATURE" >&2; exit 1; }
[[ -f "$PUBKEY" ]] || { echo "no such public key: $PUBKEY" >&2; exit 1; }

if [[ -f "$ARTIFACT.sig.json" ]]; then
  ALGORITHM=$(sed -n 's/.*"algorithm": *"\([^"]*\)".*/\1/p' "$ARTIFACT.sig.json")
  echo "algorithm: ${ALGORITHM:-unknown}"
fi

if ! openssl dgst -verify "$PUBKEY" -signature "$SIGNATURE" "$CHECKSUM" >/dev/null 2>&1; then
  echo "FAIL: ML-DSA signature over $(basename "$CHECKSUM") did not verify" >&2
  exit 1
fi
echo "PASS: signature over $(basename "$CHECKSUM")"

EXPECTED=$(cut -d' ' -f1 "$CHECKSUM")
ACTUAL=$(sha256sum "$ARTIFACT" | cut -d' ' -f1)
if [[ -z "$EXPECTED" || "$EXPECTED" != "$ACTUAL" ]]; then
  echo "FAIL: artifact sha256 mismatch (signed $EXPECTED, actual $ACTUAL)" >&2
  exit 1
fi
echo "PASS: artifact sha256 matches the signed manifest ($ACTUAL)"
echo "PASS: $(basename "$ARTIFACT") is authentic for the holder of the release key"
