# Packaging and release verification

Target: **Ubuntu 26.10 amd64**, the platform the first release is tested on.

The package is intentionally self-contained. `Qiskit`, `Qiskit Aer` and
`Babashka` are not in the Ubuntu archive, and the target's Python version is
not the one the project is tested against. The `.deb` therefore carries:

| Path | Contents |
|---|---|
| `/usr/bin/proxora` | launcher (`-lr`, `-qu`) |
| `/usr/lib/proxora/python/` | standalone CPython 3.12.13 (uv-managed build) |
| `/usr/lib/proxora/site-packages/` | NumPy, SciPy, Qiskit, Qiskit Aer and the `proxora` sources, pinned from `python/uv.lock` |
| `/usr/lib/proxora/bin/bb` | static Babashka 1.13.219 |
| `/usr/lib/proxora/clojure/src/` | the Clojure regression backend |

Runtime `Depends` are only the C/C++ runtime libraries the wheels need:
`libc6`, `libgcc-s1`, `libstdc++6`, `zlib1g`.

The Guix `sitecustomize.py` shim is **not** shipped: it exists to work around
the Guix fleet's loader, is a no-op on Ubuntu, and the bundled interpreter
uses the system glibc.

## Build

Requires network access on the build host (interpreter, wheels, Babashka) and
`uv`, `dpkg-deb`, `curl`, `fakeroot`-free ordinary user rights.

```bash
packaging/build-deb.sh
# -> dist/proxora_<version>-1_amd64.deb
```

Useful overrides: `VERSION`, `DEB_VERSION`, `PYTHON_VERSION`,
`BABASHKA_VERSION`, `WORK`, `DIST`. The CPython and Babashka versions are
pinned; Python dependencies are exported from `python/uv.lock` with hashes.

## Install and test

```bash
sudo apt install ./dist/proxora_0.1.0-1_amd64.deb
proxora -lr        # -> Prediction at x=4: 9
proxora -qu        # -> Qiskit/Aer run, exit 0
proxora --bogus    # -> usage, exit 2
sudo apt remove proxora
```

The installed program does not need the Git checkout, `uv`, a system Python,
or Babashka.

## Post-quantum artifact signing

Sign the built artifact with ML-DSA-65 (FIPS 204) using OpenSSL 3.5+:

```bash
openssl genpkey -algorithm ML-DSA-65 -out proxora-release.pem
openssl pkey -in proxora-release.pem -pubout -out proxora-release.pub.pem

PROXORA_SIGNING_KEY=proxora-release.pem packaging/sign-release.sh \
  dist/proxora_0.1.0-1_amd64.deb

packaging/verify-release.sh \
  dist/proxora_0.1.0-1_amd64.deb proxora-release.pub.pem
```

The artifact is bound to the signature through a signed **SHA-256 manifest**,
because OpenSSL 3.5's one-shot ML-DSA path fails on large inputs (the 88 MB
`.deb` cannot be signed directly):

- `<artifact>.sha256` — `sha256sum` of the artifact;
- `<artifact>.sha256.sig` — raw ML-DSA-65 signature over the manifest;
- `<artifact>.sig.json` — algorithm, digest, signer, timestamp.

Verification checks the ML-DSA signature over the manifest first, then the
artifact's actual SHA-256 against the signed digest. Replacing the artifact
therefore fails verification, and so does editing the manifest. (SHA-256 is not
known to be practically broken by quantum computers at these parameters.)

**Trust model:** this proves the artifact was signed by the holder of the
private key. It does not establish that the public key is authentic. Publish
the public key through an independent, trusted channel and pin its fingerprint.
The private key must stay offline; `packaging/keys/` and `*.sig*` are ignored by
Git.

**APT is not post-quantum here.** APT verifies repository metadata with
GPG (RSA/EdDSA), not ML-DSA. An APT repository, when added, must use standard
`InRelease`/`Release.gpg` signing; the ML-DSA signature is an additional
artifact-level check and cannot be described as something `apt install`
validates automatically. No APT repository is claimed by this release.

## Known limitations

- `proxora -qu` runs the one-qubit variational experiment in
  `python/src/proxora/__init__.py` (train `Ry(theta)` to P(1)=0.8). The full
  autoregressive variational regressor lives in `proxora.forecast.quantum` and
  is reachable through `python -m proxora.bridge` / the MCP server, not yet
  through `-qu`.
- The Kotlin MCP server is not part of this package and is not currently
  reproducibly buildable: no Gradle wrapper is committed and Gradle is not
  installed on the build host.
- The bundled components are redistributed under their own licenses; see
  `copyright` and the bundled `.dist-info` directories.
- This is a hand-assembled binary package (`dpkg-deb`), not yet a Debian
  source package with `debian/rules` and a reproducible-build attestation.
