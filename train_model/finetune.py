from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
from trl import SFTConfig, SFTTrainer

from train_model.llm_training_arg import LLMTrainingArg
from peft import LoraConfig
import datasets
import pandas as pd


def tokenize(tokenizer, prompt, max_length=1000, add_eos_token=True):
    result = tokenizer(
        prompt,
        truncation=True,
        padding=False,
        max_length=max_length,  # Enforce maximum sequence length
        return_tensors=None,
    )
    if result["input_ids"][-1] != tokenizer.eos_token_id and add_eos_token:
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


def train(config: LLMTrainingArg):
    tokenizer = AutoTokenizer.from_pretrained(config.model_dir)
    model = AutoModelForCausalLM.from_pretrained(config.model_dir, device_map="auto")

    peft_args = LoraConfig(
        lora_alpha=16,
        lora_dropout=0.1,
        r=64,
        bias="none",
        task_type="CAUSAL_LM",
    )

    training_arg = SFTConfig(
        output_dir=config.output_dir,
        num_train_epochs=2,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=1,
        optim="paged_adamw_32bit",
        learning_rate=2e-4,
        fp16=False,
        bf16=False,
        max_steps=-1,
        warmup_ratio=0.03,
        weight_decay=0.001,
        max_grad_norm=0.3,
        save_steps=25,
        logging_steps=25,
        lr_scheduler_type="constant",
    )

    #
    def generate_and_tokenize_prompt(data_point):
        full_prompt = generate_prompt(data_point)
        tokenized_full_prompt = tokenize(tokenizer, full_prompt)
        return tokenized_full_prompt

    dataset = datasets.Dataset.from_pandas(pd.read_csv(config.data_path))
    train_data = dataset.map(generate_and_tokenize_prompt, batched=True)
    print("start training")
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_data,
        peft_config=peft_args,
        max_seq_length=None,
        tokenizer=tokenizer,
        args=training_arg,
        packing=False,
    )
    print("Starting training...")
    trainer.train()
    print("Saving model...")
    trainer.model.save_pretrained(config.saved_model_dir)
