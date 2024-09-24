from typing import List, Optional

from models.trained_model import TrainedModel
from extensions import db
import logging


class TrainedModelRepo:
    @staticmethod
    def create_trainedmodel(user_id) -> TrainedModel:
        return TrainedModel(user_id=user_id)

    @staticmethod
    def save_trainedmodel(model: TrainedModel) -> Optional[TrainedModel]:
        db.session.add(model)
        try:
            db.session.commit()
            return model
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating TrainedModel for user {model.user_id}: {e}")

    @staticmethod
    def get_all_trainedmodel() -> List[TrainedModel]:
        return TrainedModel.query.all()

    @staticmethod
    def find_trainedmodel_by_user_id(user_id: int) -> TrainedModel | None:
        return TrainedModel.query.filter_by(user_id=user_id).first()

    @staticmethod
    def find_all_trainedmodel_by_user_id(user_id: int) -> List[TrainedModel]:
        return TrainedModel.query.filter_by(user_id=user_id).all()
