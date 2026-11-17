# RegistryCheck — Public Registration and Licence Verification Primitive

A standalone Intelligent Contract that attests a registration
against its registry's own public record, instead of trusting a
number printed on a website.

## Deployed

- Network: StudioNet (GenLayer Studio)
- Contract: `0x6aBEF1C312bea3d3bA37E7f067DCeEbFfd97E958`
- Deploy tx: `0xb4dd81f1f79a1ed744f02da15717a1acf3b636ed710ae9584b8ccb0ca9ce836d`
- Explorer: https://explorer-studio.genlayer.com/address/0x6aBEF1C312bea3d3bA37E7f067DCeEbFfd97E958
- Studio: https://studio.genlayer.com/?import-contract=0x6aBEF1C312bea3d3bA37E7f067DCeEbFfd97E958

## Why this exists

Before money, data or trust changes hands, the same question comes
up: is this organisation actually registered, and is that
registration still live? A company number printed on a website
proves nothing — it can be borrowed, mistyped, or left over from a
company that no longer exists. The only check that matters is the
one against the registry's own public record. RegistryCheck turns
"is this registration real and live?" into a reusable primitive
with a visible audit trail.

1. `submit_registration(entity_name, registration_number, registry_page_url)` —
   the entity, the claimed registration number and the registry
   record page are fixed at submission time.
2. `resolve_registration(registration_id)` — the LLM only extracts
   a machine line, `STATUS|FOUND_NUMBER|FOUND_NAME`, judged under
   strict equality.
3. Every decision after that is deterministic code. A live status
   is only attested when the number found on the page equals the
   claimed number exactly, and the name found on the page matches
   the claimed name.

## Dissolved is not revoked

DISSOLVED is its own state on purpose, and it is not folded into
REVOKED. A dissolved company was struck off the register and no
longer exists; a revoked licence was taken away from an entity
that may still exist. Downstream builders treat them differently —
one is "this entity is gone", the other is "this entity lost a
permission" — so the contract must not confuse them.

## State design

One-way state machine per registration:
`PENDING -> ACTIVE | EXPIRED | REVOKED | DISSOLVED | NOT_FOUND | MISMATCH`

- `ACTIVE`: the registration is live and in good standing.
- `EXPIRED`: the registration has expired or lapsed.
- `REVOKED`: the registration or licence has been revoked.
- `DISSOLVED`: the entity has been dissolved or struck off.
- `NOT_FOUND`: no such registration exists on the page.
- `MISMATCH`: the number or name found on the page does not match
  the claim, or the extraction did not produce a usable line.
  Treat as "do not act on this registration".

Because `found_number` and `found_name` are stored, anyone can see
*what* the registry actually showed, instead of getting a single
opaque verdict.

## Try it in GenLayer Studio

1. Paste `contracts/registry_check.py` into Studio and deploy (no args).
2. `submit_registration` with, for example:
   - entity_name: `BRIT ASIA ACADEMY LTD`
   - registration_number: `05293090`
   - registry_page_url: `https://find-and-update.company-information.service.gov.uk/company/05293090`
3. `resolve_registration(0)`, then `get_registration(0)` — expect
   `ACTIVE` with `found_number` `05293090` and a matching name.

## Tests

See `tests/test_cases.md` (10 cases): input validation, unknown /
double resolution, the number and name gates, and all six terminal
states.
