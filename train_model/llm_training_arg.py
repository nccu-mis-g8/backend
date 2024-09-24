from typing import Optional


class LLMTrainingArg:
    def __init__(
        self,
        model_dir: Optional[str],
        saved_model_dir: str,
        output_dir: str,
        data_path: str,
    ):
        self.model_dir = model_dir
        self.saved_model_dir = saved_model_dir
        self.output_dir = output_dir
        self.data_path = data_path

    def to_dict(self):
        return {
            "model_dir": self.model_dir,
            "output_dir": self.output_dir,
            "data_path": self.data_path,
            "saved_model_dir": self.saved_model_dir,
        }
