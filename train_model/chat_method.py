from flask import Flask, request, jsonify, Response
import json
from transformers import AutoTokenizer
import transformers
import torch


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

model = "./my-autotrain-llm"
tokenizer = AutoTokenizer.from_pretrained(model)
generator = transformers.pipeline(
    "text-generation",
    model=model,
    torch_dtype=torch.float16,
    framework="pt"
)

@app.route('/chat', methods=['POST'])
def chat():
       
    input_text = request.json.get('input_text', '')  
    instruction = "請用朋友語氣跟我聊天："  

    full_input = [{"role":"user","content":f"{instruction} {input_text}"}]

    sequences = generator(
        full_input,
        do_sample=True, 
        top_p=0.9, 
        temperature=0.7,
        num_return_sequences=1,
        eos_token_id=tokenizer.eos_token_id,
        max_length=50,
        truncation=True,
    )
    
    generated_text = sequences[0]['generated_text'] if isinstance(sequences[0], dict) else sequences[0]
    response = json.dumps({"response": generated_text}, ensure_ascii=False)
    return Response(response, content_type="application/json; charset=utf-8")
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)