from typing import List
from models.training_file import TrainingFile
from models.user import User
from extensions import db


class TrainingFileRepo:
    @staticmethod
    def create_traingfile(user: User):
        file = TrainingFile(user.id)
        db.session.add(file)
        db.session.commit()
        return file

    @staticmethod
    def get_all_trainingfile() -> List[TrainingFile]:
        return TrainingFile.query.all()

    @staticmethod
    def find_trainingfile_by_user_id(user_id):
        return TrainingFile.query.filter_by(user_id=user_id)
