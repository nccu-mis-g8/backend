from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from trl import SFTConfig, SFTTrainer
from peft import (
    LoraConfig,
    get_peft_model,
    get_peft_model_state_dict,
    prepare_model_for_kbit_training,
)
import datasets
import pandas as pd
import torch

CUTOFF_LEN = 512

BASE_MODEL_DIR = "./train_model/saved-taide-model"


def tokenize(tokenizer, prompt, add_eos_token=True):
    result = tokenizer(
        prompt,
        truncation=True,
        max_length=CUTOFF_LEN,
        padding="max_length",
        return_tensors=None,
    )
    if (
        result["input_ids"][-1] != tokenizer.eos_token_id
        and len(result["input_ids"]) < CUTOFF_LEN
        and add_eos_token
    ):
        result["input_ids"].append(tokenizer.eos_token_id)
        result["attention_mask"].append(1)

    result["labels"] = result["input_ids"].copy()

    return result


def generate_prompt(data_point):
    return (
        "以下是一個描述任務的指令，以及一個與任務資訊相關的輸入。請撰寫一個能適當完成此任務指令的回覆\n\n"
        f'### 指令：\n{data_point["instruction"]}\n\n### 輸入：\n{data_point["input"]}\n\n'
        f'### 回覆：\n{data_point["output"]}'
    )


def train(id: str, model_dir: str, save_dir: str, data_path: str):
    device_map = "auto" if torch.cuda.is_available() else "cpu"
    nf4_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL_DIR,
        add_eos_token=True,
        # 不要傳quantization_config，否則會報錯
        # quantization_config=nf4_config
    )
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        device_map=device_map,
        quantization_config=nf4_config,
    )
    if model is None:
        print("Failed to load model.")

    model = prepare_model_for_kbit_training(model)

    peft_args = LoraConfig(
        lora_alpha=16,
        lora_dropout=0.05,
        r=8,
        bias="none",
        task_type="CAUSAL_LM",
    )

    training_arg = SFTConfig(
        output_dir=f"./ouput/{id}",
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=2,
        # optim="paged_adamw_32bit",
        learning_rate=3e-4,
        # fp16=False,
        fp16=True,
        # bf16=False,
        max_steps=-1,
        warmup_ratio=0.03,
        weight_decay=0.0,  # 權重衰減
        max_grad_norm=0.3,
        save_steps=25,
        logging_steps=25,
    )

    #
    def formatting_prompts_func(example):
        output_texts = []
        for i in range(len(example["instruction"])):
            text = (
                "以下是一個描述任務的指令，以及一個與任務資訊相關的輸入。請撰寫一個能適當完成此任務指令的回覆\n\n"
                f'### 指令：\n{example["instruction"][i]}\n\n### 輸入：\n{example["input"][i]}\n\n'
                f'### 回覆：\n{example["output"][i]}'
            )
            output_texts.append(text)
        return output_texts

    #
    def generate_and_tokenize_prompt(data_point):
        full_prompt = generate_prompt(data_point)
        tokenized_full_prompt = tokenize(tokenizer, full_prompt)
        return tokenized_full_prompt

    # dataset = datasets.Dataset.from_pandas(pd.read_csv(config.data_path).head(100))
    # NOTE: 暫時把file寫死
    dataset = datasets.Dataset.from_pandas(
        # pd.read_csv("C:/Users/User/Desktop/train_data.csv").head(100)
        pd.read_csv(data_path).head(100)
    )
    train_data = dataset.map(generate_and_tokenize_prompt)
    print("start training")
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_data,
        peft_config=peft_args,
        max_seq_length=None,
        tokenizer=tokenizer,
        args=training_arg,
        formatting_func=formatting_prompts_func,
    )
    print("Starting training...")
    trainer.train()
    print("Saving model and tokenizer...")
    model.save_pretrained(save_dir)
    tokenizer.save_pretrained(save_dir)
    
    model = get_peft_model(model, peft_args)
    model.save_pretrained(save_dir)