from typing import Dict, Optional

from models.shared_model import SharedModel
from extensions import db
from models.trained_model import TrainedModel


class SharedModelRepo:
    @staticmethod
    def create_shared_model(model: TrainedModel) -> Optional[SharedModel]:
        result = SharedModel(model.id)
        db.session.add(result)
        res = SharedModelRepo.save()
        if res:
            return result
        return None

    @staticmethod
    def save() -> bool:
        try:
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False

    @staticmethod
    def obtain_shared_model(link, acquirer_id) -> Dict:
        res = {"res": False, "msg": ""}
        
        model: Optional[SharedModel] = SharedModel.query.filter_by(link=link).first()
        if model is None:
            res["msg"] = "找不到模型"
            return res
        
        if model.acquirer_id is not None:
            res["msg"] = "連結已被使用"
            return res
        
        try:
            model.acquirer_id = acquirer_id
            db.session.commit()
            res["res"] = True
            res["msg"] = "成功取得模型權限"
        except Exception as e:
            db.session.rollback()
            res["msg"] = f"資料庫錯誤: {e}"
        
        return res

