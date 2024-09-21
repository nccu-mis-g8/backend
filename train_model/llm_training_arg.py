class LLMTrainingArg:
    def __init__(
        self, model_dir: str, saved_model_dir: str, output_dir: str, data_path: str
    ):
        self.model_dir = model_dir
        self.saved_model_dir = saved_model_dir
        self.output_dir = output_dir
        self.data_path = data_path
