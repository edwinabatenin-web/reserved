# QuickBooks Q-S5B bounded sync evidence

Status: uncommitted, network-inert candidate for independent review.
QuickBooks remains disabled.

## Bounded outcome

`reserved/providers/accounting/quickbooks_sync_evidence.py` validates mechanics
for already-retrieved QuickBooks Invoice or Payment query pages and one bounded
Invoice CDC response. It does not make provider calls, construct URLs, access
credentials or configuration, persist evidence, adapt canonical accounting
objects, or activate QuickBooks.

The query boundary requires one exact opaque request identity to be re-presented
on every page of the run, exact minor version 75, one exact entity type,
one-based contiguous positions, a requested page size from 1 to 1,000, exact
response counts, non-decreasing retrieval evidence, unique Q-S4-observed
entity identities, and an observed short or empty terminal page. Pages from
different request identities cannot be spliced. A separately reported count
may corroborate the number fetched, but it does not make separate calls a
stable snapshot. Query ordering and snapshot fitness therefore remain
explicitly unverified.

The CDC boundary accepts only an already-retrieved Invoice response covering
at most 30 days. It validates exact live Invoice records through Q-S4, validates
exact deleted tombstones separately, preserves provider response order only as
evidence, rejects duplicate/live-deleted identity conflicts, and permits an
empty response. Exactly 1,000 objects is retained as saturation evidence and
cannot be called complete; more than 1,000 fails closed. Local retrieval time
is provenance, not a provider watermark.

## Fact and inference boundary

The dated facts in `QUICKBOOKS_QS5_PROVIDER_FACTS.md` support minor version 75,
one entity per query, one-based `STARTPOSITION`, `MAXRESULTS` up to 1,000,
separate `COUNT(*)`, filterable `MetaData.LastUpdatedTime`, CDC look-back of at
most 30 days, a 1,000-object CDC cap, changed groups, empty responses, and
deleted tombstones.

The provider-local page progression and short-page termination checks are
conservative implementation mechanics. They are not claims of provider
ordering or snapshot isolation. Matching a separate count cannot eliminate
changes between calls. Likewise, a bounded CDC response does not establish
boundary inclusivity, a safe next watermark, continuous coverage, or complete
history. Those limitations remain in every result.

## Fail-closed and prohibited uses

Before interpreting any field, the contract traverses and bounds the complete
run/response graph. It rejects aliases and cycles, excessive aggregate pages,
records, nodes, depth, width or bytes, unsafe control/format/surrogate/private/
unassigned Unicode, malformed or custom containers, wrong JSON scalar types,
entity mixing, page gaps or overlaps,
contradictory counts, missing terminal evidence, duplicate identities,
Q-S1 binding substitution, unsupported CDC groups, malformed tombstones,
out-of-window metadata, and object-cap overflow. Controlled errors and result
representations do not contain source data.

Every accepted result remains unverified for canonical ingestion. It cannot be
used as evidence of stable ordering, snapshot completeness, continuous CDC,
historical completeness, settlement or tax meaning, provider activation,
sandbox success, production readiness, or launch readiness. Payment CDC is not
supported. No Q-S2 transport, Q-S3 route/custody, broader Q-S5 ingestion, or
Q-S6 operational gate is implemented here.

Shared `ResourceCompleteness` dimensions remain conservative: coherent request
identity allows the bounded run-mechanics result to be recorded, but pagination
ordering, independent totals, known exclusions/filter semantics, CDC deletion
coverage, freshness, and continuous-chain evidence remain unknown (or
incomplete at the documented CDC saturation boundary).

## Residual external evidence

Before a later package can claim complete ingestion it still needs reviewed
provider evidence for stable unique ordering, query snapshot semantics across
count/page calls, authoritative response metadata, CDC boundary inclusivity
and next-watermark behaviour, truncation signalling, and any Payment CDC or
deletion shape. This package deliberately reports those dimensions as unknown
or unverified instead of inventing them.
