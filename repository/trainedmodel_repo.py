from typing import List

from sqlalchemy import desc

from models.trained_model import TrainedModel
from extensions import db


class TrainedModelRepo:
    @staticmethod
    def create_trainedmodel(user_id) -> TrainedModel:
        model = TrainedModel(user_id=user_id, end_time=None)
        db.session.add(model)
        TrainedModelRepo.save()
        return model

    @staticmethod
    def save() -> bool:
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False

    @staticmethod
    def get_all_trainedmodel() -> List[TrainedModel]:
        return TrainedModel.query.all()

    @staticmethod
    def find_trainedmodel_by_user_id(user_id: int) -> TrainedModel | None:
        return TrainedModel.query.filter_by(user_id=user_id).first()

    @staticmethod
    def find_all_trainedmodel_by_user_id(user_id: int) -> List[TrainedModel]:
        return (
            TrainedModel.query.filter_by(user_id=user_id)
            .order_by(TrainedModel.start_time)
            .all()
        )
