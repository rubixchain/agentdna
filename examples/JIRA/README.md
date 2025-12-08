# Jira MCP Agent – (Streamlit, Gemini, MCP)

This project provides a complete **Jira AI Agent** using:

- **Model Context Protocol** for tool execution  
- **FastMCP** Jira MCP server (`server.py`)  
- **Gemini** as the backbone LLM
- **Streamlit UI** (`app.py`) for an interactive web interface   

The agent allows you to query Jira issues, create tasks, transition workflow states, and add comments through a simple chat interface.

---

## Features

### Jira MCP Server (server.py)
Implements Jira tools:

- `search_issues(jql, max_results=10)`
- `get_issue(key)`
- `create_issue(project_key, summary, description, issue_type="Task")`
- `add_comment(issue_key, comment)`
- `transition_issue(issue_key, transition_name)`

Implemented using `FastMCP`.

### Streamlit Chat UI (app.py)
- Multi-turn UI with message history  
- Calls the MCP agent for each user query (if found necessary)
- Displays:
  - Final agent answer  
  - Which Jira MCP tool was used  
  - JSON arguments   

---

## Folder Structure

```
JIRA/
│
├── app.py                  
├── server.py               
├── client.py               
├── agent.py                
├── .env.example                    
└── README.md               
```

---

## Installation

### 1. Install Dependencies

```
pip install streamlit google-genai python-dotenv "mcp[cli]"
```

### 2. Create a `.env` file

```
GEMINI_API_KEY=your_gemini_key
JIRA_BASE_URL=https://yourdomain.atlassian.net
JIRA_EMAIL=your_email@example.com
JIRA_API_TOKEN=your_jira_api_token
```

## Running the Agent

```
cd JIRA
streamlit run app.py
```

(auto) Open:  
http://localhost:8501

### Example Prompts

- show my latest Jira issues
- create a task in project TEST with summary "Bug from agent"
- move AURA-2 to In Progress
- add comment to TEST-10 saying work completed

---

## Architecture Overview

```
Streamlit UI (app.py)
        │
        ▼
Gemini LLM
        │
JSON decision
        │
        ▼
MCP Client (app.py)
        │
        ▼
MCP Server (server.py)
        │
Jira REST API
```

---
