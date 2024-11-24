from transformers import (
    Trainer,
    TrainingArguments,
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
)
import datasets
import pandas as pd
import torch
import gc

CUTOFF_LEN = 512

BASE_MODEL_DIR = "./train_model/saved-taide-model"


def cleanup_model(model):
    del model
    gc.collect()
    torch.cuda.empty_cache()


def tokenize(tokenizer, prompt, output_text, add_eos_token=True):
    prompt_result = tokenizer(
        prompt,
        truncation=True,
        max_length=CUTOFF_LEN,
        padding="max_length",
        return_tensors="pt",
    )

    # Tokenize output_text
    output_result = tokenizer(
        output_text,
        truncation=True,
        max_length=CUTOFF_LEN,
        padding="max_length",
        return_tensors="pt",
    )

    # 合併 input_ids 和 labels，注意 EOS token 的處理
    input_ids = prompt_result["input_ids"].squeeze(0).tolist()
    labels = prompt_result["input_ids"].squeeze(0).tolist()

    # 將 output_text 附加到 labels
    labels.extend(output_result["input_ids"].squeeze(0).tolist())

    # 添加 EOS token
    if add_eos_token and len(labels) < CUTOFF_LEN:
        labels.append(tokenizer.eos_token_id)

    attention_mask = [1] * len(input_ids)

    return {
        "input_ids": input_ids[:CUTOFF_LEN],
        "attention_mask": attention_mask[:CUTOFF_LEN],
        "labels": labels[:CUTOFF_LEN],
    }


def generate_prompt(data_point):
    instruction = data_point.get("instruction", "")
    input_text = data_point.get("input", "")
    output_text = data_point.get("output", "")

    # 調整
    prompt = f"""<s>[INST] <<SYS>>請依照情境做正確、合理以及和過去類似語氣的回答<</SYS>>
        {instruction}

        {input_text}
    [/INST]"""
    return prompt, output_text


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

    model = get_peft_model(model, peft_args)

    training_args = TrainingArguments(
        output_dir=f"./ouput/{id}",
        num_train_epochs=3,
        per_device_train_batch_size=8,
        gradient_accumulation_steps=2,
        learning_rate=3e-4,
        fp16=True,
        max_steps=-1,
        warmup_ratio=0.03,
        weight_decay=0.0,
        max_grad_norm=0.3,
        save_steps=25,
        logging_steps=25,
    )

    def generate_and_tokenize_prompt(data_point):
        prompt, output_text = generate_prompt(data_point)
        return tokenize(tokenizer, prompt, output_text)

    dataset = datasets.Dataset.from_pandas(pd.read_csv(data_path))
    train_data = dataset.map(generate_and_tokenize_prompt)
    print("start training")

    trainer = Trainer(
        model=model,
        train_dataset=train_data,
        tokenizer=tokenizer,
        args=training_args,
    )

    print("Starting training...")
    trainer.train()

    print("Saving model and tokenizer...")
    model.config.save_pretrained(save_dir)
    tokenizer.save_pretrained(save_dir)

    model.save_pretrained(save_dir)
    cleanup_model(model)
    print("Training and saving completed.")
