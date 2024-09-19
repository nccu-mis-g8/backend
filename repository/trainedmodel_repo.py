from typing import List

from models.trained_model import TrainedModel
from models.user import User
from extensions import db


class TrainedModelRepo:
    @staticmethod
    def create_trainedmodel(user: User):
        file = TrainedModel(user.id)
        db.session.add(file)
        db.session.commit()
        return file

    @staticmethod
    def get_all_trainedmodel() -> List[TrainedModel]:
        return TrainedModel.query.all()

    @staticmethod
    def find_trainedmodel_by_user_id(user_id):
        return TrainedModel.query.filter_by(user_id=user_id)
