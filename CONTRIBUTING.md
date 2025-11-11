# Contributing to Multi-Agent Stock Research Pipeline

Thank you for your interest in contributing to Multi-Agent Stock Research Pipeline!
This project demonstrates a production-ready multi-agent LangGraph workflow for end-to-end equity research — integrating retrieval, compliance filtering, analysis generation, and automated reporting.
We welcome contributions in the form of bug fixes, new features, agent improvements, documentation, and research content enhancements.
---

# How to Get Started

1. **Read the README.md**

   The README covers all the essentials, including:

   - Environment setup (venv, dependencies, .env variables)

   - Running agents (Data, Analyst, Compliance, Supervisor, and Publisher)

   - Building and querying reports via the CLI and FastAPI server

   - Regenerating artifacts (PDF, Markdown, JSON, and Charts)

   - Logging, monitoring, and error handling
   

2. **Fork and Clone**
```bash
git clone https://github.com/mohanelango/multiagent-stock-research.git
cd multiagent-stock-research
```

3. **Create a branch**
```bash
git checkout -b feature/my-feature
```
---
### Guidelines

- Follow PEP8 code style. Run black src tests before committing.

- Keep commits descriptive, e.g.:
     - feat: add sentiment-analysis agent
   
     - fix: handle missing FMP API response
   
     - docs: update orchestration diagram
   
     - chore: refactor logging with RotatingFileHandler
   
     - Add/update tests for any new feature or bug fix.

- Documentation

  - Update the architecture or flow diagrams in /docs if you modify orchestration logic.

  - Include docstrings for every class, function, and agent.

  - Keep the README and CONTRIBUTING files consistent with your changes.
---
### Typical Areas for Contribution

- Agent Enhancements

  - Improve LangGraph orchestration logic.

  - Add new agents (e.g., “Risk Analyzer Agent,” “Valuation Agent”).

- Performance Optimization

  - Reduce latency in data retrieval (yFinance, FMP).

  - Enhance caching or memory management in multi-agent runs.

- Reporting Improvements

  - Extend Report Publisher to support HTML or DOCX exports.

  - Enhance charts or add AI commentary summaries.

- Compliance & Logging

  - Improve keyword filters, redaction logic, or term matching.

  - Refine logging and error alerting mechanisms.

- Documentation & Demos

  - Add architecture diagrams or example runs.

  - Create short video demos or Jupyter notebooks showing workflows.
---
### Submitting Your Work
1. Push your branch to your fork:
```bash
git push origin feature/add-new-agent
```
2. Open a Pull Request (PR) to the main branch.

3. In your PR, include:

   - A summary of your change

   - Screenshots or logs (if relevant)

   - Confirmation that all tests pass locally
---
### Code of Conduct
[CODE OF CONDUCT](CODE_OF_CONDUCT.md).