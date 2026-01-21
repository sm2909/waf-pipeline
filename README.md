# Transformer-Based Web Application Firewall (WAF) for Zero-Day Attack Detection

## Overview

This project implements an anomaly-based Web Application Firewall (WAF) that uses a Transformer (GPT-2) trained exclusively on benign web application traffic. Instead of relying on static signatures, the system learns normal HTTP request patterns and detects anomalous or malicious requests in real time by scoring request sequences with a causal language model (perplexity).

The implementation is intended for security research, demos, and hackathon prototypes — demonstrating how modern language models can be adapted for zero-day detection in web traffic.

## Key Features

- Reverse-proxy deployment using Nginx in front of a vulnerable web application (OWASP Juice Shop).
- Log ingestion from Nginx access logs (batch and live traffic).
- Parsing and normalization of HTTP requests (method, path, parameter ordering, basic sanitization).
- Tokenization of normalized requests into Transformer-friendly sequences.
- Fine-tuning a pre-trained GPT-2 model on benign traffic (GPU-friendly workflow using Google Colab).
- Unsupervised anomaly detection using perplexity scoring of request sequences.
- Real-time, non-blocking inference via a FastAPI microservice.
- Live detection of malicious payloads injected via `curl` or automated scripts.
- Modular pipeline suitable for incremental retraining and experimentation.

## System Architecture

High-level flow:

- Browser → Nginx (WAF placement) → Juice Shop
- Nginx → FastAPI WAF service → GPT-2 inference
- Logs → Normalization → Tokenization → Model training

In operation, Nginx acts as the reverse proxy in front of the application and forwards request metadata (and optionally bodies) to the FastAPI WAF service for scoring. All traffic is logged to Nginx access logs; logs are normalized and tokenized for batch training and threshold calibration.

## Tech Stack

- Python 3.9+ (core services)
- Hugging Face Transformers
- PyTorch (training & inference)
- FastAPI (real-time scoring microservice)
- Nginx (reverse proxy / WAF placement)
- Docker (Juice Shop demo)
- Google Colab (training with GPUs)
- Linux (Fedora development environment)

## Setup Instructions

Below are high-level steps to run the demo locally. Adjust paths and ports to fit your environment.

--first you need to clone the juice shop app from https://github.com/juice-shop/juice-shop.git

1. Start OWASP Juice Shop (Docker)

```bash
docker run --rm -p 3000:3000 bkimminich/juice-shop
```

2. Configure Nginx as a reverse proxy

Create a site config that forwards traffic to Juice Shop and forwards metadata to the FastAPI WAF service. Minimal example (add to your nginx `sites-available`):

```nginx
server {
  listen 80;
  server_name localhost;

  location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Host $host;
    access_log /var/log/nginx/juice_access.log combined;
  }
}
```

3. Generate benign traffic

- Use browsers, automated Selenium scripts, or `wrk`/`ab` to generate typical user interactions for Juice Shop to create benign training data.

4. Extract and normalize logs

- Run the included normalization pipeline (examples in `parse_logs.py` / `normalize_logs.py`) to transform Nginx access records into the normalized request representation used for tokenization and training.

5. Train GPT-2 on Google Colab

- Upload `train_tokens.txt` (or use a mounted Google Drive). Use Hugging Face Transformers + `Trainer` to fine-tune GPT-2 on benign sequences. See the Model Training section below for details.

6. Run FastAPI WAF service

```bash
# from the project root
uvicorn waf_service:app --host 0.0.0.0 --port 8000 --workers 1
```

7. Test anomaly detection

- Send benign and malicious requests (examples below) and observe scoring and logs.

## Model Training

Why GPT-2
- GPT-2 is a causal language model that estimates the conditional likelihood of token sequences. This supports probabilistic scoring (per-token log-probabilities and sequence perplexity), making it suitable for unsupervised anomaly detection on sequential text-like data such as tokenized HTTP requests.

Tokenization strategy
- Normalize requests into a canonical textual form containing method, path, sorted query parameters, and a deterministic representation of body or headers when included.
- Use a custom tokenizer vocabulary derived from tokenizing normalized requests and merging with GPT-2's tokenizer (or extend via `special_tokens_map.json`) to capture common HTTP atoms (methods, separators, encodings).

Training process (high level)

- Prepare a dataset of benign sequences: one normalized request per line, tokenized into GPT-2 tokens.
- Use `DataCollatorForLanguageModeling` to create batches for causal LM fine-tuning (no masked LM).
- Use Hugging Face `Trainer` with `GPT2LMHeadModel` and standard causal LM loss.
- Recommended: mixed precision (fp16) and gradient accumulation if sequences are long.

Threshold selection

- After training, compute the perplexity distribution on a held-out benign validation set. Choose a detection threshold (e.g., mean + k * std) based on your desired false positive rate and operational constraints.
- Store thresholds and use them during live scoring.

## Anomaly Detection Logic

Perplexity calculation
- For a given normalized & tokenized request x = (x1...xn), the model produces token log-probabilities. The sequence negative log-likelihood is summed across tokens; perplexity is:

$$\text{Perplexity}(x)=\exp\left( -\frac{1}{n} \sum_{i=1}^{n} \log p(x_i|x_{<i}) \right)$$

Threshold derivation
- Calculate perplexity for many benign requests and choose an operational threshold. Typical approach: set threshold to a percentile (e.g., 99th) of benign perplexities or mean + 3σ depending on risk tolerance.

Operational behavior (non-blocking)
- The FastAPI service scores requests and logs anomalies to a secure audit store or SIEM but by default forwards traffic to the upstream application (non-blocking). This enables monitoring without impacting availability.
- A separate blocking mode can be enabled to drop or challenge requests with perplexity above a higher enforcement threshold.

Logging & observability
- For each request the WAF logs: normalized request, token length, perplexity, threshold used, detection decision, and metadata (timestamp, source IP).

## Demo Instructions

Start services (one-liners):

```bash
# Start Juice Shop
docker run --rm -p 3000:3000 bkimminich/juice-shop &

# Start FastAPI WAF (ensure model & tokenizer paths are configured)
uvicorn waf_service:app --host 0.0.0.0 --port 8000

# Ensure Nginx is running and proxying to Juice Shop
sudo systemctl restart nginx
```

Example benign request (curl)

```bash
curl -i http://localhost/ # proxied to Juice Shop
```

Expected WAF log entry (example)

```json
{
  "request": "GET /api/score?item=1",
  "perplexity": 12.3,
  "threshold": 50.0,
  "anomaly": false
}
```

Example malicious request (SQL injection)

```bash
curl -i "http://localhost/search?q=' OR 1=1 --"
```

Expected WAF log entry (example)

```json
{
  "request": "GET /search?q=' OR 1=1 --",
  "perplexity": 620.4,
  "threshold": 50.0,
  "anomaly": true
}
```

Note: the exact numeric values depend on model, tokenizer, and training data.

## Future Improvements

- Incremental fine-tuning: continuously update the model on newly observed benign traffic using a FIFO or reservoir of past benign samples.
- Blocking mode enforcement: add configurable blocking or challenge behavior for very high perplexity scores.
- Header and body inspection: extend normalization to include selected headers or body fields (careful with PII and privacy).
- Multi-app support: allow separate models or domain adapters per hosted application.
- Model optimization: quantization, distillation, or ONNX export to reduce inference latency for high-throughput deployments.

## Files & Useful Scripts

- `parse_logs.py` — log parsing helpers.
- `normalize_logs.py` — normalization routines to canonicalize requests.
- `prepare_training_data.py` — tokenization and dataset preparation.
- `waf_service.py` — FastAPI real-time scoring service.
- `generate_benign.sh` — example benign traffic generator for Juice Shop.

## Security & Privacy Notes

- This project is intended for research and demo use. Avoid forwarding or storing sensitive payloads in logs without proper redaction and user consent.
- When deploying in production, ensure model artifacts, logs, and thresholds are protected and rotated according to organizational policy.


---

Project maintained in this repository. For quick access to the generated README, see [README.md](README.md).
