# Multi-Agent Stock Market Research (Powered by LangChain + LangGraph)

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/langchain-0.2.0-purple.svg)](https://github.com/langchain-ai/langchain)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-ready-brightgreen.svg)](https://fastapi.tiangolo.com)
[![Works with GPT-5](https://img.shields.io/badge/LLM-GPT--5-black.svg)](https://platform.openai.com)

---

## Why This Project Exists

The world of financial research has evolved — analysts now rely on automation, AI, and real-time data instead of Excel sheets and manual fundamentals.  
This project demonstrates a **Minimal-production-ready multi-agent research system** built using **LangChain + LangGraph**, designed to automate:

-  Historical stock price analysis  
-  Fundamental data fetching  
-  News tracking  
-  Analyst-style report generation  
-  Compliance filtering  
-  PDF + Markdown Research Reports with charts  

Whether you're a developer, quant researcher, analyst, or AI enthusiast — this repo shows how to build **real-world LLM-enabled workflows** that generate institutional-quality research without requiring paid API data feeds.

---

##  Key Features

| Feature                        | Description |
|--------------------------------|------------|
| **4-Agent Architecture**       | DataAgent, AnalystAgent, ComplianceAgent, SupervisorAgent |
| **Charts + Stats**             | Auto-generates return stats + matplotlib price chart |
| **Live News Feed Integration** | Fetches RSS news headlines related to your stock symbol |
| **PDF Report Generation**      | Produces clean markdown AND PDF research output |
| ️ **Free Data Sources**        |yfinance + FMP "demo" endpoints + public RSS feeds |
| **FastAPI Endpoint**           | `/analyze` route returns report paths + JSON response |
| **Error Handling**             | Skips unknown symbols, logs edge cases, continues pipeline |
| **Human-In-Loop (Optional)** | Approve generated reports before publishing |

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Orchestration | LangGraph, LangChain |
| Backend APIs | FastAPI |
| LLM Model | GPT-5 via OpenAI |
| Data Tools | yFinance, FinancialModelingPrep (fallback), RSS |
| File Formats | Markdown, JSON, PDF |
| Logging | Rotating log file via `logging` + `TimedRotatingFileHandler` |
| Code Quality | Black, Ruff, Pytest |
| PDF Rendering | Pandoc + wkhtmltopdf |
| Python | 3.10+ |

---

## Installation

```bash
git clone https://github.com/mohanelango/multiagent-stock-research.git
cd multiagent-stock-research
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` to select your preferred LLM provider (OpenAI / Ollama / HF).  
Optionally tune `configs/settings.yaml` for chunk size, retrieval `k`, or model parameters.

---

## How It Works

Every time you run a stock analysis, four distinct agents collaborate:

1. Data Agent → Fetches prices, fundamentals, and news

2. Analyst Agent → Writes the narrative & market interpretation

3. Compliance Agent → Screens content for restricted words

4. Supervisor Agent → Merges, formats, and publishes outputs

They communicate via a LangGraph state machine and are orchestrated end-to-end through CLI or API.

---
## Architecture Diagram (Mermaid)

graph TD

A[User Input] --> B[LangGraph Orchestrator]
B --> C[Data Agent]
C --> D[Analyst Agent]
D --> E[Compliance Agent]
E --> F[Supervisor Agent]
F -->|Outputs| G[Markdown Report]
F -->|Outputs| H[JSON Data]
F -->|Outputs| I[PDF Export]
---
### Usage (CLI)
```python
python -m src.cli --symbol AAPL --days 30 --outdir artifacts
```
### Outputs:
```bash
== Outputs ==
report: artifacts/AAPL/AAPL_2025-10-25_report.md
plot: artifacts/AAPL/AAPL_chart.png
raw: artifacts/AAPL/AAPL_raw.json
pdf: artifacts/AAPL/AAPL_2025-10-25_report.pdf
```
### Auto-created folder: artifacts/AAPL/

    AAPL_2025-10-25_report.md → Full report (Markdown)
    
    AAPL_2025-10-25_report.pdf → Exported PDF
    
    AAPL_raw.json → Raw collected data
    
    AAPL_chart.png → Price returns chart
---
## REST API (FastAPI)
### Start the server:
```bash
uvicorn src.api:app --reload --port 8000

```
Example call:
```
curl -X POST http://127.0.0.1:8000/analyze \
-H "Content-Type: application/json" \
-d '{"symbol":"META","days":10}'
```
Response:
```json
{
  "symbol": "META",
  "report": "artifacts/META/META_2025-10-25_report.md",
  "pdf": "artifacts/META/META_2025-10-25_report.pdf",
  "plot": "artifacts/META/META_chart.png",
  "raw": "artifacts/META/META_raw.json"
}

```
## Contributing
PRs are welcome! Whether you're fixing a bug, improving PDF formatting, or adding a new tool — open a PR and let's build better agent workflows together

---
## License
MIT License © 2025
Feel free to use, modify, and distribute this for personal or enterprise use.