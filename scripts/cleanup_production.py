"""
Documented Production Cleanup Script.
Deletes exclusively agent-created test users and records:
- m1_test_* users and all associated contacts, batches, AI keys, profiles, purposes
- vikassdangi@gmail.com account created by agent (user will sign up themselves)
- Outputs detailed audit of all deleted IDs and counts.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packages.shared.db import create_db_engine, create_session_factory
from packages.shared.schema import (
    User, Profile, Purpose, Batch, Contact, AIKey, SenderRelay, Attachment, DoNotContact
)
from apps.api.config import settings

def run_cleanup():
    engine = create_db_engine(settings.DATABASE_URL)
    factory = create_session_factory(engine)
    
    with factory() as session:
        target_users = session.query(User).filter(
            (User.email == "vikassdangi@gmail.com") | (User.email.like("m1_test_%"))
        ).all()
        
        target_user_ids = [u.id for u in target_users]
        print(f"Found {len(target_users)} target users to delete:")
        for u in target_users:
            print(f"  - User: {u.email} (ID: {u.id})")

        if not target_user_ids:
            print("No matching users found. Nothing to delete.")
            return

        # 1. Contacts
        contacts = session.query(Contact).filter(Contact.user_id.in_(target_user_ids)).all()
        print(f"\nDeleting {len(contacts)} contacts:")
        for c in contacts:
            print(f"  - Contact: {c.email} (Status: {c.status}, ID: {c.id})")
        session.query(Contact).filter(Contact.user_id.in_(target_user_ids)).delete(synchronize_session=False)

        # 2. Batches
        batches = session.query(Batch).filter(Batch.user_id.in_(target_user_ids)).all()
        print(f"\nDeleting {len(batches)} batches:")
        for b in batches:
            print(f"  - Batch: {b.name} (Status: {b.status}, ID: {b.id})")
        session.query(Batch).filter(Batch.user_id.in_(target_user_ids)).delete(synchronize_session=False)

        # 3. Purposes
        purposes = session.query(Purpose).filter(Purpose.user_id.in_(target_user_ids)).all()
        print(f"\nDeleting {len(purposes)} purposes:")
        for p in purposes:
            print(f"  - Purpose: {p.name} (ID: {p.id})")
        session.query(Purpose).filter(Purpose.user_id.in_(target_user_ids)).delete(synchronize_session=False)

        # 4. AI Keys
        ai_keys = session.query(AIKey).filter(AIKey.user_id.in_(target_user_ids)).all()
        print(f"\nDeleting {len(ai_keys)} AI keys:")
        for k in ai_keys:
            print(f"  - AIKey: provider={k.provider}, status={k.status} (ID: {k.id})")
        session.query(AIKey).filter(AIKey.user_id.in_(target_user_ids)).delete(synchronize_session=False)

        # 5. Profiles
        profiles = session.query(Profile).filter(Profile.user_id.in_(target_user_ids)).all()
        print(f"\nDeleting {len(profiles)} profiles:")
        for pr in profiles:
            print(f"  - Profile: {pr.full_name} (ID: {pr.id})")
        session.query(Profile).filter(Profile.user_id.in_(target_user_ids)).delete(synchronize_session=False)

        # 6. Relays, Attachments, DoNotContact
        session.query(SenderRelay).filter(SenderRelay.user_id.in_(target_user_ids)).delete(synchronize_session=False)
        session.query(Attachment).filter(Attachment.user_id.in_(target_user_ids)).delete(synchronize_session=False)
        session.query(DoNotContact).filter(DoNotContact.user_id.in_(target_user_ids)).delete(synchronize_session=False)

        # 7. Users
        session.query(User).filter(User.id.in_(target_user_ids)).delete(synchronize_session=False)

        session.commit()
        print(f"\n[OK] Successfully deleted {len(target_user_ids)} users and all associated child entities.")

if __name__ == "__main__":
    run_cleanup()
