from flask import Blueprint, request, Response, jsonify
import logging
import json
from transformers import AutoTokenizer
import transformers
import torch
from train_model.finetune import train

train_model_bp = Blueprint("train_model", __name__)
logger = logging.getLogger(__name__)

default_config = {
    "project_name": "my-autotrain-llm",
    "model_name": "./saved-taide-model",
    "data_path": "./train_model",
    "lr": 2e-4,
    "epochs": 4,
    "batch_size": 1,
    "block_size": 1024,
    "trainer": "sft",
    "warmup_ratio": 0.1,
    "weight_decay": 0.01,
    "gradient_accumulation": 4,
    "peft": True,
    "lora_r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.045,
    "dataset_name":"train.csv"
}

model = "./my-autotrain-llm"
tokenizer = AutoTokenizer.from_pretrained(model)
generator = transformers.pipeline(
    "text-generation", model=model, torch_dtype=torch.float16, framework="pt"
)


@train_model_bp.post("/training_file")
def upload_training_file():
    pass


@train_model_bp.post("/train_model")
def train_model():
    try:
        custom_config = request.json
        if not custom_config:
            custom_config = default_config

        train_config = {**default_config, **custom_config}

        train(train_config)
        return (
            jsonify(
                {"status": "Training started successfully", "config": train_config}
            ),
            200,
        )
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500


@train_model_bp.post("/chat")
def chat():
    input_text = request.json.get("input_text", "")
    instruction = "請你以和過去回答相同的語氣回答問題，注意你回答的內容要符合對方的問題。"

    full_input = [{"role": "system", "content": instruction},{"role": "user", "content": f"{input_text}"}]

    sequences = generator(
        full_input,
        do_sample=True,
        top_p=0.9,
        temperature=0.7,
        num_return_sequences=1,
        eos_token_id=tokenizer.eos_token_id,
        max_length=70,
        truncation=True,
    )

    generated_text = ""
    for message in sequences[0]["generated_text"]:
        if message["role"] == "assistant":
            generated_text = message["content"]
            break

    response = json.dumps({"response": generated_text}, ensure_ascii=False)
    return Response(response, content_type="application/json; charset=utf-8")
