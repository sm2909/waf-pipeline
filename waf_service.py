from fastapi import FastAPI, Request
import uvicorn
import torch
import math
from transformers import GPT2Tokenizer, GPT2LMHeadModel

# Load trained GPT-2 model
model_dir = "waf_gpt2"
tokenizer = GPT2Tokenizer.from_pretrained(model_dir)
tokenizer.pad_token = tokenizer.eos_token
model = GPT2LMHeadModel.from_pretrained(model_dir)
model.eval()
model.to("cuda" if torch.cuda.is_available() else "cpu")

# Threshold (set based on benign data)
THRESHOLD = 4  # example, adjust after stats collection

app = FastAPI()

# Normalization helper
def normalize_request(method, path, query_present):
    path = path.replace("?", " ? ").replace("/", " / ")
    query_flag = " QUERY = True" if query_present else " QUERY = False"
    return f"method_{method} path_{path}{query_flag}"

# Perplexity function
def compute_perplexity(text):
    encodings = tokenizer(text, return_tensors="pt", truncation=True, max_length=64)
    encodings = {k: v.to(model.device) for k, v in encodings.items()}
    with torch.no_grad():
        outputs = model(**encodings, labels=encodings["input_ids"])
        loss = outputs.loss
    return math.exp(loss.item())

@app.post("/inspect")
async def inspect(request: Request):
    data = await request.json()
    method = data.get("method", "GET")
    path = data.get("path", "/")
    query_present = bool(data.get("query", False))

    normalized = normalize_request(method, path, query_present)
    ppl = compute_perplexity(normalized)

    result = {"perplexity": ppl, "anomaly": ppl > THRESHOLD}
    if ppl > THRESHOLD:
        print(f"Anomaly detected: {normalized} (perplexity={ppl:.2f})")
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
