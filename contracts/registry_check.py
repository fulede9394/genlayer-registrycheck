# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import typing


class RegistryCheck(gl.Contract):
    """
    RegistryCheck - a public registration and licence verification
    primitive.

    Before money, data or trust changes hands, the same question
    comes up: is this organisation actually registered, and is
    that registration still live? A company number printed on a
    website proves nothing - it can be borrowed, mistyped, or
    left over from a company that no longer exists. The only
    check that matters is the one against the registry's own
    public record.

    This contract attests a registration against its registry's
    public page. The entity name, the claimed registration number
    and the registry record page are fixed at submission time,
    and the verdict is taken by consensus against the live page.
    A fresh check is a fresh record: a registration can lapse,
    be revoked or be dissolved, so a past verdict is never
    evidence about today.

    Consensus follows the structured-extraction pattern: the LLM
    only extracts a machine line, it never decides the outcome.

      STATUS|FOUND_NUMBER|FOUND_NAME

    STATUS is ACTIVE, EXPIRED, REVOKED, DISSOLVED or NOT_FOUND,
    FOUND_NUMBER is the registration number as shown on the
    page and FOUND_NAME is the entity name as shown on the
    page. That line is judged under strict_eq, so validators
    must extract the same status, the same number and the same
    name.

    Every decision after that is deterministic code, and that is
    the point. A live status is only attested when the number
    found on the page equals the claimed number exactly, and the
    name found on the page matches the claimed name. A record
    that loads fine but belongs to a different entity can never
    produce a false ACTIVE: it ends in MISMATCH.

    DISSOLVED is its own state on purpose, and it is not folded
    into REVOKED. A dissolved company was struck off the register
    and no longer exists; a revoked licence was taken away from
    an entity that may still exist. Downstream builders treat
    them differently - one is "this entity is gone", the other
    is "this entity lost a permission" - so the contract must
    not confuse them.
    """

    registration_count: u256
    entity_names: TreeMap[u256, str]
    registration_numbers: TreeMap[u256, str]
    registry_pages: TreeMap[u256, str]
    statuses: TreeMap[u256, str]
    found_numbers: TreeMap[u256, str]
    found_names: TreeMap[u256, str]

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    DISSOLVED = "DISSOLVED"
    NOT_FOUND = "NOT_FOUND"
    MISMATCH = "MISMATCH"

    def __init__(self):
        self.registration_count = u256(0)

    def _name_matches(self, claimed: str, found: str) -> bool:
        # At least one significant word (four letters or more)
        # from the claimed name must appear in the name found on
        # the page. Short words (LTD, THE, AND, OF) prove nothing.
        claimed_lower = claimed.lower()
        found_lower = found.lower()
        if claimed_lower in found_lower or found_lower in claimed_lower:
            return True
        words = claimed_lower.split(" ")
        for word in words:
            if len(word) >= 4 and word in found_lower:
                return True
        return False

    @gl.public.write
    def submit_registration(
        self, entity_name: str, registration_number: str, registry_page_url: str
    ) -> int:
        entity_name = entity_name.strip()
        registration_number = registration_number.strip()
        registry_page_url = registry_page_url.strip()

        assert len(entity_name) >= 5, "entity name too short"
        assert len(entity_name) <= 200, "entity name too long"
        assert len(registration_number) >= 5, "registration number too short"
        assert len(registration_number) <= 30, "registration number too long"
        assert registry_page_url.startswith("https://"), "registry page must be https"
        assert len(registry_page_url) <= 300, "registry page URL too long"

        rid = self.registration_count
        self.entity_names[rid] = entity_name
        self.registration_numbers[rid] = registration_number
        self.registry_pages[rid] = registry_page_url
        self.statuses[rid] = self.PENDING
        self.found_numbers[rid] = ""
        self.found_names[rid] = ""
        self.registration_count = rid + u256(1)
        return int(rid)

    @gl.public.write
    def resolve_registration(self, registration_id: int) -> str:
        rid = u256(registration_id)
        assert rid in self.statuses, "unknown registration"
        assert self.statuses[rid] == self.PENDING, "registration already resolved"

        # Copy storage into locals: non-deterministic blocks may not
        # touch contract storage, they may only capture local values.
        entity_name = self.entity_names[rid]
        registration_number = self.registration_numbers[rid]
        registry_page_url = self.registry_pages[rid]

        def extract_registration() -> str:
            page = gl.nondet.web.render(registry_page_url, mode="text")
            prompt = f"""Check one public registration using only the registry page below.

Entity: {entity_name}
Claimed registration number: {registration_number}

Page content:
{page[:4000]}

Reply with exactly one line, nothing else, in this format:
STATUS|FOUND_NUMBER|FOUND_NAME

STATUS is one of:
ACTIVE - the registration is live and in good standing
EXPIRED - the registration has expired or lapsed
REVOKED - the registration or licence has been revoked
DISSOLVED - the entity has been dissolved or struck off the register
NOT_FOUND - no such registration exists on this page

FOUND_NUMBER is the registration number exactly as shown on the page. If there is no registration number on the page, write NONE.
FOUND_NAME is the entity name exactly as shown on the page. If there is no entity name on the page, write NONE."""
            return gl.nondet.exec_prompt(prompt).strip()

        line = gl.eq_principle.strict_eq(extract_registration)

        # Deterministic parsing and decision. The LLM extracted
        # data; it never decided the outcome.
        first_sep = line.find("|")
        if first_sep == -1:
            self.statuses[rid] = self.MISMATCH
            return self.MISMATCH
        rest = line[first_sep + 1:]
        second_rel = rest.find("|")
        if second_rel == -1:
            self.statuses[rid] = self.MISMATCH
            return self.MISMATCH

        status_word = line[:first_sep].strip().upper()
        found_number = rest[:second_rel].strip()
        found_name = rest[second_rel + 1:].strip()
        self.found_numbers[rid] = found_number
        self.found_names[rid] = found_name

        if status_word == "NOT_FOUND":
            final = self.NOT_FOUND
        elif status_word == "ACTIVE" or status_word == "EXPIRED" or status_word == "REVOKED" or status_word == "DISSOLVED":
            number_ok = found_number.upper() == registration_number.upper()
            name_ok = self._name_matches(entity_name, found_name)
            if number_ok and name_ok:
                final = status_word
            else:
                final = self.MISMATCH
        else:
            final = self.MISMATCH

        self.statuses[rid] = final
        return final

    @gl.public.view
    def get_registration(self, registration_id: int) -> typing.Any:
        rid = u256(registration_id)
        assert rid in self.statuses, "unknown registration"
        return {
            "id": registration_id,
            "entity": self.entity_names[rid],
            "registration_number": self.registration_numbers[rid],
            "registry_page": self.registry_pages[rid],
            "status": self.statuses[rid],
            "found_number": self.found_numbers[rid],
            "found_name": self.found_names[rid],
        }

    @gl.public.view
    def get_status(self, registration_id: int) -> str:
        rid = u256(registration_id)
        assert rid in self.statuses, "unknown registration"
        return self.statuses[rid]

    @gl.public.view
    def is_active(self, registration_id: int) -> bool:
        rid = u256(registration_id)
        assert rid in self.statuses, "unknown registration"
        return self.statuses[rid] == self.ACTIVE

    @gl.public.view
    def get_registration_count(self) -> int:
        return int(self.registration_count)
