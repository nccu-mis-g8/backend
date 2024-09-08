from transformers import AutoTokenizer
import transformers
import torch

model = "./my-autotrain-llm"

tokenizer = AutoTokenizer.from_pretrained(model)

print("Generating text...")
pipeline = transformers.pipeline(
    "text-generation",
    model=model,
    torch_dtype=torch.float16,
    framework="pt"
)

input_text = '你等等有課嗎？ 請用朋友語氣回答我：'

sequences = pipeline(
    input_text,
    do_sample=True,
    top_p=0.9,
    temperature=0.6,
    top_k=10,
    num_return_sequences=1,
    eos_token_id=tokenizer.eos_token_id,
    max_length=50,
    truncation=True,
)

for seq in sequences:
    generated_text = seq['generated_text']
    result = generated_text.replace(input_text,"").replace('「', '').replace('」', '').strip()
    print(f"Result: {result}")