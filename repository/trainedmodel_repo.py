from typing import List, Optional

from sqlalchemy import desc

from models.trained_model import TrainedModel
from extensions import db


class TrainedModelRepo:
    @staticmethod
    def is_model_id_exists(model_id):
        return TrainedModel.query.filter_by(id=model_id).scalar() is not None

    @staticmethod
    def create_trainedmodel(
        user_id, model_original_name, modelphoto=None, anticipation=None
    ) -> TrainedModel:
        if modelphoto == "":
            modelphoto = None
        if anticipation == "":
            anticipation = None
        model = TrainedModel(
            user_id=user_id,
            model_original_name=model_original_name,
            modelphoto=modelphoto,
            anticipation=anticipation,
            end_time=None,
        )
        db.session.add(model)
        TrainedModelRepo.save()
        return model

    @staticmethod
    def start_trainedmodel(user_id, model_id) -> Optional[TrainedModel]:
        model = TrainedModel.query.filter_by(user_id=user_id, id=model_id).first()
        model.start_time = db.func.now()
        TrainedModelRepo.save()
        return model

    @staticmethod
    def save() -> bool:
        try:
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False

    @staticmethod
    def get_all_trainedmodel() -> List[TrainedModel]:
        return TrainedModel.query.all()

    @staticmethod
    def find_trainedmodel_by_user_id(user_id: int) -> TrainedModel | None:
        return TrainedModel.query.filter_by(user_id=user_id).first()

    @staticmethod
    def find_trainedmodel_by_user_and_model_id(
        user_id, model_id
    ) -> TrainedModel | None:
        return TrainedModel.query.filter_by(user_id=user_id, id=model_id).first()

    @staticmethod
    def find_all_trainedmodel_by_user_id(user_id: int) -> List[TrainedModel]:
        return (
            TrainedModel.query.filter_by(user_id=user_id)
            .order_by(TrainedModel.start_time)
            .all()
        )
