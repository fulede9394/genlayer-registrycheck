# RegistryCheck — test cases

Run manually in GenLayer Studio after deploying
`contracts/registry_check.py` (no constructor args).

## Deterministic validation

1. `submit_registration` with an entity name shorter than 5
   characters — expect rejection ("entity name too short").
2. `submit_registration` with a registration number shorter than
   5 characters — expect rejection ("registration number too
   short").
3. `submit_registration` with an `http://` (non-https) registry
   page URL — expect rejection ("registry page must be https").
4. `submit_registration("BRIT ASIA ACADEMY LTD", "05293090", "https://find-and-update.company-information.service.gov.uk/company/05293090")` — expect
   registration id `0`, and `get_registration_count()` returns `1`.
5. `get_status(99)` on an unknown registration — expect rejection
   ("unknown registration").
6. `resolve_registration(99)` on an unknown registration — expect
   rejection ("unknown registration").

## Non-deterministic verdict paths

7. Resolve the BRIT ASIA ACADEMY LTD registration from case 4 —
   expect `ACTIVE`, with `found_number` `05293090` and a matching
   name, and `is_active(0)` returns `true`.
8. Submit STATUS INTERIORS LIMITED — registration number
   `11560652`, page
   `https://find-and-update.company-information.service.gov.uk/company/11560652`
   — and resolve it. Expect `DISSOLVED`, not `REVOKED`: the
   company was dissolved on 2020-02-18.
9. Submit BRIT ASIA ACADEMY LTD again, but with the wrong
   registration number (`05293091`), on the same page, and resolve
   it — expect `MISMATCH`, not `ACTIVE`. The number found on the
   page does not equal the claimed number.
10. Resolve an already-resolved registration a second time — expect
    rejection ("registration already resolved"). A registration
    that resolved to `ACTIVE` stays `ACTIVE` in its own record;
    submit a new registration for a fresh check.
