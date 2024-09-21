"""
api 那可以直接call finetune.train(your_config)
"""


from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
from trl import SFTConfig, SFTTrainer

from train_model.llm_training_arg import LLMTrainingArg
from peft import LoraConfig
from datasets import load_dataset


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

    print("start training")
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
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
