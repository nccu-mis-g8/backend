from typing import Dict, Optional

from sqlalchemy import false
from models.shared_model import SharedModel


class SharedModelRepo:
    @staticmethod
    def create_shared_model(owener_id) -> SharedModel:
        result = SharedModel(owener_id)
        return result

    @staticmethod
    def obtain_shared_model(id, acquirer_id) -> Dict:
        res = {"res": False, "msg": ""}
        model: Optional[SharedModel] = SharedModel.query.filter_by(id=id).first()
        if model is None:
            res["msg"] = "找不到模型"
            return res
        # if model 被取走了
        if model.acquirer_id is not None:
            res["msg"] = "連結己被使用"
            return res
        return res
