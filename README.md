# Multi-Agent Stock Market Research (Powered by LangChain + LangGraph)

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/langchain-0.3.27-purple.svg)](https://github.com/langchain-ai/langchain)
![LLM](https://img.shields.io/badge/Orchestrator-Langgraph-red)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-ready-brightgreen.svg)](https://fastapi.tiangolo.com)
[![Works with GPT-5](https://img.shields.io/badge/LLM-GPT--5-black.svg)](https://platform.openai.com)
![AIEngineering](https://img.shields.io/badge/Discipline-AI_Engineering-purple)
![LangChain](https://img.shields.io/badge/Framework-LangChain-orange)
![LLM](https://img.shields.io/badge/Model-LLM-black)
![LLM](https://img.shields.io/badge/Data-Agent-blue)
![LLM](https://img.shields.io/badge/Analyst-Agent-lightgreen)
![LLM](https://img.shields.io/badge/Compliance-Agent-red)
![LLM](https://img.shields.io/badge/Supervisor-Agent-orange)
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
| ️**Free Data Sources**        |yfinance + FMP "demo" endpoints + public RSS feeds |
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
Edit `.env` and add your FMP_API_KEY from [https://site.financialmodelingprep.com/](FMP).  
Optionally tune `configs/settings.yaml` to select your preferred LLM provider (OpenAI,Gemini), max_news, strict_mode.

    ⚠️ Important: PDF export requires:
         1. pandoc (document conversion)
         2. wkhtmltopdf (HTML-to-PDF engine)
         3. pypandoc (Python binding to Pandoc) (already available in requirement.txt. So no need to install separately)

    (If you don’t have Chocolatey, install from https://chocolatey.org/install
    first — it’s one line. Once Done follow the below installation via chocolatey.)

🔹 Windows (via Chocolatey)
```bash
# Install Pandoc
choco install pandoc -y

# Install wkhtmltopdf
choco install wkhtmltopdf -y
```
🔹 macOS (via Homebrew)
```bash
# Install Pandoc
brew install pandoc

# Install wkhtmltopdf
brew install wkhtmltopdf
```
🔹 Linux (Debian/Ubuntu)
```bash
sudo apt update
sudo apt install python3-pip pandoc wkhtmltopdf -y

```


---

## How It Works

Every time you run a stock analysis, four distinct agents collaborate:

1. Data Agent → Fetches prices, fundamentals, and news

2. Analyst Agent → Writes the narrative & market interpretation

3. Compliance Agent → Screens content for restricted words

4. Supervisor Agent → Merges, formats, and publishes outputs

They communicate via a LangGraph state machine and are orchestrated end-to-end through CLI or API.

---
## Architecture Overview

![Architecture Example](docs/Multiagent.svg)

This architecture diagram shows how a stock symbol request flows through a LangGraph-powered multi-agent pipeline — from data collection, AI analysis, and compliance filtering to final report generation and artifact export.
For a deeper explanation, see [`docs/architecture.md`](docs/architecture.md)

---
### Usage (CLI)
```python
python -m src.cli --symbol AAPL --days 10 --outdir artifacts
```
### Sample CLI Output:
![CLI Example](docs/Screenshots/cli.png)

### Auto-created folder: artifacts/AAPL/

    AAPL_2025-11-09_report.md → Full report (Markdown)
    
    AAPL_2025-11-09_report.pdf → Exported PDF
    
    AAPL_raw.json → Raw collected data
    
    AAPL_chart.png → Price returns chart
---
## REST API (FastAPI)
### Start the server:
```bash
uvicorn src.api:app --reload --port 8000
```
### Example call:
```
curl -X POST http://127.0.0.1:8000/analyze \
-H "Content-Type: application/json" \
-d '{"symbol":"META","days":10}'
```
### Sample API Output:
![CLI Example](docs/screenshots/api.png)
---
### Sample Chart Output:
![CLI Example](artifacts/META/META_chart.png)
---

## Tests & Quality Assurance

This repository uses pytest for unit and integration testing.
Mock-based tests validate the behavior of each Agent independently (DataAgent, AnalystAgent, ComplianceAgent, SupervisorAgent).
### Run All Tests
```bash
pytest -v --disable-warnings
```
### Run a Single Test File
```bash
pytest tests/test_analyst_agent.py -v
```
---
## Contributing
PRs are welcome! Whether you're fixing a bug, improving PDF formatting, or adding a new tool — open a PR and let's build better agent workflows together.

---
## License
Distributed under the [MIT License](LICENSE).