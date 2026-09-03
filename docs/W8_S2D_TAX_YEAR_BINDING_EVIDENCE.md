# W8-S2D tax-year binding evidence

This bounded package preserves the exact conventional tax year issued by the
reviewed `AnnualToCashPosition` producer through the W8 customer-result identity
and deterministic API JSON projection.

The annual/cash handoff does not accept a caller-supplied tax year. It reads the
field only from the live producer-issued value after issuance validation, and
the producer identity check detects subsequent mutation. The public result
requires an exact `YYYY/YY` string whose suffix is the following year, includes
that value in its integrity seal and content identity, and the API reconstructs
and revalidates it from an immutable primitive capture before returning it.

This package adds no persistence, route, provider activation, credentials,
payment authority, recalculation, wording change, launch claim, or production
access.
