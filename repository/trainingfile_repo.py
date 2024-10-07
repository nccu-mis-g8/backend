from typing import List, Optional
from models.training_file import TrainingFile
from extensions import db
import logging


class TrainingFileRepo:
    @staticmethod
    def create_trainingfile(user_id, filename, original_file_name) -> Optional[TrainingFile]:
        file = TrainingFile(user_id=user_id, filename=filename, original_file_name=original_file_name)
        db.session.add(file)
        try:
            db.session.commit()
            return file
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating training_file for user {user_id}: {e}")
            return None

    @staticmethod
    def get_all_trainingfile() -> List[TrainingFile]:
        return TrainingFile.query.all()

    @staticmethod
    def find_trainingfile_by_user_id(user_id) -> List[TrainingFile]:
        return TrainingFile.query.filter_by(user_id=user_id).all()

    # 取得已訓練的file
    @staticmethod
    def find_training_file_by_user_id(user_id) -> List[TrainingFile]:
        return TrainingFile.query.filter_by(user_id=user_id, is_trained=True).all()

    # 取得未訓練的file
    @staticmethod
    def find_not_training_file_by_user_id(user_id) -> List[TrainingFile]:
        return TrainingFile.query.filter_by(user_id=user_id, is_trained=False).all()

    @staticmethod
    def find_first_training_file_by_user_id(user_id) -> Optional[TrainingFile]:
        return TrainingFile.query.filter_by(user_id=user_id).first()

    @staticmethod
    def delete_training_file_by_file_id(file_id):
        TrainingFile.query.filter_by(id=file_id).delete()
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error delete training_file for file {file_id}: {e}")

    @staticmethod
    def save_training_file():
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating file: {e}")
            return None
