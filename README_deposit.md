# CAUCHY — frozen ensemble v1 and Paper 2 Phase 2 records

Persistent homology of the DESI Bright Galaxy Survey: data, code and integrity manifests
supporting M26 (MNRAS MN-26-2100-P) and Paper 1 (MN-26-2388-P).

Concept DOI: [10.5281/zenodo.21128856](https://doi.org/10.5281/zenodo.21128856)
Author: Alessandro Marconi — ORCID [0009-0002-3682-1815](https://orcid.org/0009-0002-3682-1815)
Repository: https://github.com/AleMarco1/CAUCHY

---

## 1. What "ensemble v1" means

Ensemble v1 is the frozen mock ensemble produced by `voxelize_mock` with **unit weights**,
as used for every number in M26 (including R1) and in Paper 1. It is immutable. Paper 2
may create an ensemble v2 (FKP-weighted mock voxelisation); no number may be reported
without an explicit v1 or v2 label. The unqualified phrase "fiducial ensemble" is retired.

The reference set `src/paper2_v1_reference.json` holds the numbers every script must
reproduce before reporting anything new:

| | N_H1(DESI) | mock mean | mock sd (ddof=1) | n | deficit | empirical rank |
|---|---:|---:|---:|---:|---:|---|
| NGC | 28 256 | 35 436.686 | 312.989 | 2000 | 20.26% | 1/2001 |
| SGC | 15 122 | 18 712.968 | 197.787 | 2000 | 19.19% | 1/2001 |

---

## 2. Contents

| file | contents |
|---|---|
| `cauchy_code.zip` | source tree (`src/`), licence, git attributes |
| `cauchy_manifests_v1.zip` | the six freeze manifests (header + body), reference set, amendment log |
| `cauchy_records_v1.zip` | tier `records`: 224 text artefacts, 20.7 MB |
| `cauchy_paper2_products.zip` | tier `paper2_products`: 28 Phase 2 result files, 0.8 MB |
| `MANIFEST.sha256` | digests of everything above, coreutils format |

The archives are **reproducible**: fixed timestamps, fixed permissions, sorted entry
names. Rebuilding them from the same sources yields the same SHA-256, so `MANIFEST.sha256`
is a check and not a snapshot.

```
sha256sum -c MANIFEST.sha256
```

### What is not uploaded, and why

The four binary tiers total 28.7 GB and are not included:

| tier | files | bytes | contents |
|---|---:|---:|---|
| `features` | 12 189 | 24 326 788 | TDA feature vectors |
| `fields` | 2 202 | 18 472 477 342 | density fields |
| `diagrams` | 16 221 | 4 488 929 201 | persistence diagrams and Betti curves |
| `superseded` | 4 000 | 5 739 175 578 | superseded persistence diagrams |

Their **manifests are included**. Anyone holding the data can recompute the aggregate
digests below and establish that their copy is bit-identical to the one used in the
papers, without needing any code from this deposit. The full tree is available from the
author on request.

---

## 3. Integrity

Six tiers, 34 864 files in total. Each tier has a header
(`ensemble_v1_freeze_{tier}.json`: rules, counts, aggregate) and a body
(`ensemble_v1_manifest_{tier}.jsonl`: one record per file, with `rel`, `sha256`, `bytes`).

| tier | files | bytes | `aggregate_sha256` |
|---|---:|---:|---|
| records | 224 | 20 710 671 | `5364cf2ef1cac16c66e2f80dcd897bee8d14324100f15d0c9b471085f4b876f0` |
| features | 12 189 | 24 326 788 | `b0601f36c89430b3133b46e6107a0c13f50f55a8626fefcc808a6ec3d8d21fcc` |
| fields | 2 202 | 18 472 477 342 | `bf176f95a3b9e31d0c78590a2d7eef1fdc6ecd2bbf5efc4388358ca5724a2c34` |
| diagrams | 16 221 | 4 488 929 201 | `3a746c95e009b89a3a66408880b3085abe41e5f1e5c9ac12ee05009ae08f4929` |
| superseded | 4 000 | 5 739 175 578 | `f2cf37627a44e4475a8a19b19d7631b0a094098e509220f1f5a0267bffb33764` |
| paper2_products | 28 | 815 823 | `3062b7de04db4654a18bc0c6171a501d597f5d76353c76ce3dd1e474cb6aab7b` |

The five v1 tiers sum to 34 836 files and 28 745 619 580 bytes (26.77144 GiB).

### Recomputing an aggregate

Three lines, no dependency on this repository:

```python
import hashlib, json
recs = {}
for line in open("ensemble_v1_manifest_records.jsonl", encoding="utf-8"):
    r = json.loads(line); recs[r["rel"]] = r["sha256"]      # last write wins
print(hashlib.sha256("\n".join(sorted(f"{k}:{v}" for k, v in recs.items()))
                     .encode()).hexdigest())
```

No trailing newline; the sort is on the composed `path:digest` string; paths are stored
POSIX-style, so the digest is platform-independent. The bodies are append-only, so a path
may occur more than once and the last record wins.

The five v1 tiers were rebuilt from scratch on 28 August 2026, with every per-file record
rewritten, and all five aggregates were unchanged. The freeze therefore depends only on
file contents and paths, not on filesystem metadata or on repository state.

### Two different digests of the reference set

`src/paper2_v1_reference.json` is described by two quantities, and they are **not** two
versions of the file:

- `_self_sha256` = `865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc`
  — SHA-256 of the file's *content* re-serialised canonically
  (`json.dumps(indent=2, sort_keys=True, ensure_ascii=False)` after removing the field
  itself). This is the gate every script checks before reporting numbers, and the value
  the manifests record in `reference_sha256`.
- SHA-256 of the file's *bytes* = `332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d`,
  11 306 bytes.

The reference set has never been modified. Where the two published numbers differ, they
are measuring different things.

### Amendments

`src/paper2_v1_amendments.jsonl` is append-only. Frozen values are never edited in place;
a correction is a new record carrying `old_value`, `new_value`, `reason` and `evidence`.
A reader overlays the amendments on the frozen values rather than merging them.

---

## 4. Reproducing the analysis

Python 3.11, with `numpy`, `scipy`, `astropy` and `gudhi`.

```
python src/paper2_freeze_verify.py verify        # all tiers, four directions
python src/paper2_freeze_verify.py selftest      # the verifier checks itself first
```

`verify` checks header against body, body against disk, and — the direction a per-line
check does not have — replays each tier's declared rules over the filesystem to find files
that satisfy them and are absent from the manifest. A truncated manifest passes a per-line
check precisely because it checks fewer things.

Input data: DESI BGS DR1 (AJ 171, 285, 2026; [10.3847/1538-3881/ae4c43](https://doi.org/10.3847/1538-3881/ae4c43))
and 2000 Quijote mock catalogues, both obtained from their respective public archives and
not redistributed here.

---

## 5. A note on the `records` tier

Eighteen files in `records` are named `phase*_review.json` or `phase*_gate_result.json`
and contain fields such as `reviewer_verdict`. These are **internal review cycles of the
CAUCHY framework**, in which a second model instance audited each phase before its gate
was evaluated. They are not peer review material and contain no third-party text. They are
included because they document why each decision was taken.

---

## 6. Licence and citation

Code: MIT (see `LICENSE` in `cauchy_code.zip`). Data and manifests: CC-BY-4.0.

Please cite the concept DOI [10.5281/zenodo.21128856](https://doi.org/10.5281/zenodo.21128856)
together with the relevant paper.
