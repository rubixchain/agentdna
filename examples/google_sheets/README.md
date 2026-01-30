# MCP For Google Sheets (agentdna protected)

A **Streamlit demo app** that spins up a local **MCP server** for Google Sheets (via stdio) and calls its tools from the UI


---

## Repo structure

```text
mcp-gsheets/
├─ credentials/
│  └─ service_account.json                                   
├─ app.py                         
├─ server.py  
├─ requirements.txt     
├─ .env.example                
```

---

## Prerequisites

- Python **3.9+**
- A Google Cloud **Service Account JSON** with access to Google Sheets
- Google Sheets API enabled in your Google Cloud project

---

## 1) Setup

### Create a virtualenv (recommended)

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate  # Windows
```

### Install dependencies

```bash
pip install -r requirements.txt
```


---

## 2) Configure environment variables

Copy the template:

```bash
cp .env.example .env
```

Edit `.env` and fill in the values.


---

## 3) Google Sheets access

1. Put your service account key file at:
   ```text
   credentials/service_account.json
   ```
2. Open the Google Sheet you want to use and **share it** with the service account email:
   - Find it in the JSON under `client_email`
3. Make sure the Sheet tab has the expected header row (or start with an empty sheet and let the server create it)

---

## 4) Run the demo (this is the main way)

Start Streamlit:

```bash
streamlit run app.py
```

That’s it and the app will spawn `server.py` automatically

---

## Troubleshooting

**`Missing AGENTDNA_API_KEY`**
- Set `AGENTDNA_API_KEY` in `.env`. The AgentDNA API Key can be acqiored form signing up 

**Google auth / permissions errors**
- Confirm `GOOGLE_APPLICATION_CREDENTIALS=credentials/service_account.json`
- Share the spreadsheet with the service account `client_email`.
- Ensure Google Sheets API is enabled in your GCP project.

**Header row mismatch**
- This demo expects a specific header row in the configured sheet tab.
- Easiest fix: use a fresh sheet tab (empty) so the server can initialize it.


