from typing import List, Optional
from models.training_file import TrainingFile
from extensions import db
import logging


class TrainingFileRepo:
    @staticmethod
    def create_trainingfile(user_id) -> Optional[TrainingFile]:
        file = TrainingFile(user_id=user_id)
        db.session.add(file)
        try:
            db.session.commit()
            return file
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating TrainedModel for user {user_id}: {e}")
            return None

    @staticmethod
    def get_all_trainingfile() -> List[TrainingFile]:
        return TrainingFile.query.all()

    @staticmethod
    def find_trainingfile_by_user_id(user_id) -> List[TrainingFile]:
        return TrainingFile.query.filter_by(user_id=user_id).all()
