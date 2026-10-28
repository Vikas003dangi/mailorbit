import csv
import io
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from packages.shared.schema import Contact

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

# Common column name variations (normalized: lowercased, alphanumeric only)
EMAIL_KEYS = {"email", "emailaddress", "mail", "contactemail", "leademail", "workemail", "recruiteremail"}
NAME_KEYS = {"name", "fullname", "contactname", "firstname", "hrname", "recruitername", "personname"}
COMPANY_KEYS = {"company", "companyname", "org", "organization", "firm", "employer", "client"}
ROLE_KEYS = {"role", "jobrole", "title", "position", "designation", "jobtitle"}


class ImportResult(BaseModel):
    total_rows: int
    valid_count: int
    imported_count: int
    duplicates_dropped: int
    invalid_format_count: int
    errors: List[str] = []


def normalize_column_name(col: str) -> str:
    return re.sub(r"[^a-z0-9]", "", col.lower().strip())


def map_row(raw_row: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Maps arbitrary column headers to standard contact fields."""
    mapped: Dict[str, Optional[str]] = {
        "email": None,
        "name": None,
        "company": None,
        "role": None,
    }

    for key, val in raw_row.items():
        if val is None:
            continue
        val_str = str(val).strip()
        if not val_str:
            continue

        clean_key = normalize_column_name(str(key))
        if (clean_key in EMAIL_KEYS or "email" in clean_key) and not mapped["email"]:
            mapped["email"] = val_str
        elif (clean_key in NAME_KEYS or "name" in clean_key) and not mapped["name"]:
            mapped["name"] = val_str
        elif (clean_key in COMPANY_KEYS or "company" in clean_key) and not mapped["company"]:
            mapped["company"] = val_str
        elif (clean_key in ROLE_KEYS or "role" in clean_key) and not mapped["role"]:
            mapped["role"] = val_str

    return mapped


def parse_csv_content(content: str) -> List[Dict[str, Any]]:
    """Parses raw CSV string into a list of dictionaries."""
    f = io.StringIO(content.strip())
    reader = csv.DictReader(f)
    return [row for row in reader if any(row.values())]


def process_contact_import(
    db: Session,
    user_id: uuid.UUID,
    raw_rows: List[Dict[str, Any]],
    purpose_id: Optional[uuid.UUID] = None,
) -> Tuple[ImportResult, List[Contact]]:
    """
    Validates, deduplicates against both the payload and existing database rows,
    and bulk-persists new contacts for the given user.
    """
    total = len(raw_rows)
    seen_in_payload = set()
    valid_new_rows: List[Dict[str, Optional[str]]] = []
    invalid_format_count = 0
    duplicates_dropped = 0
    errors: List[str] = []

    # 1. Payload-level validation and deduplication
    for idx, raw in enumerate(raw_rows, start=1):
        mapped = map_row(raw)
        email = (mapped["email"] or "").lower().strip()

        if not email:
            invalid_format_count += 1
            errors.append(f"Row {idx}: Missing email address")
            continue

        if not EMAIL_REGEX.match(email):
            invalid_format_count += 1
            errors.append(f"Row {idx}: Invalid email format: {email}")
            continue

        if email in seen_in_payload:
            duplicates_dropped += 1
            continue

        seen_in_payload.add(email)
        mapped["email"] = email
        valid_new_rows.append(mapped)

    if not valid_new_rows:
        return (
            ImportResult(
                total_rows=total,
                valid_count=0,
                imported_count=0,
                duplicates_dropped=duplicates_dropped,
                invalid_format_count=invalid_format_count,
                errors=errors,
            ),
            [],
        )

    # 2. Database-level deduplication: find existing emails for this user
    incoming_emails = [r["email"] for r in valid_new_rows]
    existing_contacts = (
        db.query(Contact.email)
        .filter(Contact.user_id == user_id, Contact.email.in_(incoming_emails))
        .all()
    )
    existing_set = {row[0].lower() for row in existing_contacts}

    # 3. Create Contact entities for genuinely new contacts
    contacts_to_create: List[Contact] = []
    for r in valid_new_rows:
        if r["email"] in existing_set:
            duplicates_dropped += 1
            continue

        contact = Contact(
            user_id=user_id,
            purpose_id=purpose_id,
            email=r["email"],
            name=r["name"],
            company=r["company"],
            role=r["role"],
            status="PENDING",
        )
        contacts_to_create.append(contact)

    if contacts_to_create:
        db.add_all(contacts_to_create)
        db.commit()
        for c in contacts_to_create:
            db.refresh(c)

    result = ImportResult(
        total_rows=total,
        valid_count=len(valid_new_rows),
        imported_count=len(contacts_to_create),
        duplicates_dropped=duplicates_dropped,
        invalid_format_count=invalid_format_count,
        errors=errors[:10],  # Return up to 10 sample errors to avoid huge payloads
    )

    return result, contacts_to_create
