# C0 convergence manifest

Status: uncommitted convergence candidate; not independently assured and not authority to begin downstream implementation.

## Engineering identities

- Accounting v3 base: `1ded2b19f8c5ba2ea528c69796f62420b3e00a67`.
- Accounting bundle SHA-256: `377de18ebf43caccd896f264165bf6247a12886e4c81df77512138ebd926b184`.
- HICBC evidence head: `07195ef1adddbf019edade7473ae68f404432d84`.
- HICBC bundle SHA-256 actually present and independently rehashed: `f752ac1183a4a56084ec3766ea9e2bd21ee004d1f0cb53eb43f54b32382c5e32`. The earlier recorded digest beginning `f752acbb` is superseded for this file.
- Imported HICBC functional commits, in order: `93ddf94`, `c06fd0d`, `de334e4`, `d773f4b`, `8af2c20`, `72cfa82`, `2313382`.
- HICBC metadata-only commits deliberately excluded: `7eef301`, `079b5cc`, `2af2a82`, `47eef32`, `07195ef`.

The imported HICBC functional diff is staged so its provenance remains distinct. C0 reconciliation and Accounting F-01 edits remain unstaged until independent review. Reported F-01 commits `7da1356` and `8bdcedc`, and FreeAgent candidate `cd077c0`, were unavailable in the inspected object stores and bundles; they are not treated as verified engineering identities.

## Bounded correction and scope reconciliation

Accounting F-01 is recreated narrowly against v3: the canonical tax-input gate receives an independently established business base currency, rejects absent or malformed base-currency evidence, and requires validated conversion evidence when document and business currencies differ. It does not enable or implement a provider.

Founder Decisions are reconciled for the statutory HICBC claimant/equal-ANI rule, Payments on Account, Blind Person's Allowance, the Simplified Tax Health Check, and October geography. October supports England, Wales and Northern Ireland. Scotland, the Republic of Ireland/Ireland and other non-UK jurisdictions are excluded or deferred. This convergence does not implement PoA or BPA.

## Shared and protected boundaries

- `FOUNDER_DECISIONS.md` is the principal cross-workstream policy-collision surface.
- `reserved/assurance_metadata.json` is generated evidence. It is not hand-merged or edited during uncommitted convergence.
- Provider adapters and readiness controls remain disabled/protected until their own evidence gates pass.
- `reserved_west/**`, release/build scripts and independent fixture expectations are not general implementation surfaces.
- The two HICBC fixture files in this diff come from the verified functional chain. Their expected values and integrity relationship must be reviewed, not adjusted merely to make tests pass.

## Verification order

1. Review the exact staged import and unstaged C0 diff.
2. Run focused Accounting F-01/compatibility and HICBC/integrated tests.
3. Run structural, fixture-integrity and full maintained tests.
4. After explicit commit authority, commit the exact approved source diff.
5. Build the deterministic artefact from that exact commit and run the complete canonical release gate.
6. Only after the gate succeeds, regenerate assurance metadata from that result and commit it separately.
7. Independently verify the committed source, artefact identity, gate result and metadata.

Historical metadata cannot establish the converged source is sound.

## Downstream ownership and readiness

C0 establishes a coherent base and assigns boundaries; it does not freeze the contract between annual tax liability and HMRC cash obligations. W1 owns the supported annual-position scope and included allowances/reliefs. W2 owns Payments on Account, tax already paid, remaining HMRC cash obligations, due dates and the eventual annual-to-cash contract. That contract is frozen only after PoA implementation and evidence exist.

After an explicit `AUTHORISE DOWNSTREAM BUILD` decision, the following can be issued immediately where their starting identities are pinned:

- W1 requirements/implementation for confirmed annual-position gaps;
- W2 PoA and cash-obligation work;
- provider-specific disabled-first packages using the converged Accounting contract;
- UX and user testing against stable journey contracts;
- E2E and launch-hardening preparation.

Requirements refinement, independent test design, UX research and provider evidence preparation can be checkpointed on the MacBook Air before migration where they do not edit shared implementation files. No downstream package is authorised by this document.

## Migration boundary

C0 supplies the source commit, bundle digests, branch/ref inventory, dirty-diff identity, protected-file map, dependency/test-environment description, provider enablement state and verification commands for a later MacBook Pro manifest. The cutover itself is a separate bounded operation: transfer one authoritative Git state, verify hashes and refs, rebuild the test environment, rerun focused/full checks, and prevent two writable authoritative copies.

## Residual evidence and blockers

- The converged diff requires independent review, an approved commit, canonical gate execution and post-commit verification.
- F-01 is a bounded reconstruction because its reported commits were unavailable.
- Provider adapters remain disabled and require provider-specific evidence and sandbox/target-environment validation.
- HICBC remains subject to its privacy, retention, legal/security and annual-integration launch gates.
- PoA, BPA and the final annual-to-cash obligation contract remain downstream implementation work.
- Target-environment and provider journeys remain external evidence requirements.

These items do not prevent independent review of C0. They do prevent treating this uncommitted candidate as launch-ready.
