from typing import List, Optional
import uuid
from extensions import db
import logging

from models.trust_report import TrustReport


class TrustReportRepo:
    @staticmethod
    def create_trust_report(user_id, filename) -> Optional[TrustReport]:
        file = TrustReport(
            user_id=user_id,
            filename=filename,
        )
        db.session.add(file)
        try:
            db.session.commit()
            return file
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating training_file for user {user_id}: {e}")
            return None
