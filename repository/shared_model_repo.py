from typing import Dict, Optional

from models.shared_model import SharedModel
from extensions import db


class SharedModelRepo:
    @staticmethod
    def create_shared_model(model_id) -> Optional[SharedModel]:
        result = SharedModel(model_id)
        try:
            db.session.commit()
            return result
        except Exception:
            db.session.rollback()
            return None

    @staticmethod
    def obtain_shared_model(link, acquirer_id) -> Dict:
        res = {"res": False, "msg": ""}
        model: Optional[SharedModel] = SharedModel.query.filter_by(link=link).first()
        if model is None:
            res["msg"] = "找不到模型"
            return res
        # if model 被取走了
        if model.acquirer_id is not None:
            res["msg"] = "連結己被使用"
            return res
        res["res"] = True
        res["msg"] = "成功取得模型"
        model.acquirer_id = acquirer_id
        return res
