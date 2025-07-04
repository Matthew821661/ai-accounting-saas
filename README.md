# AI Accounting SaaS — pdfplumber Edition

**An AI-driven bookkeeping prototype** built with Streamlit & OpenAI, using pdfplumber for PDF parsing—no Java required.

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
streamlit run app.py
```

## Features

- Upload bank statements (PDF via pdfplumber & Excel)
- GPT-powered GL account classification
- Manual & adjusting journal entries
- Trial balance & VAT summary (15% SA VAT)

## License

MIT
