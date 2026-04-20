# SE4458 — Assignment 2: Airline AI Agent

An AI-powered chat application for managing airline operations (search flights, book tickets, check-in) using **MCP (Model Context Protocol)** architecture with a local LLM.

## 📹 Video Demo

> **Video Link:** [TODO: Add your video link here]

---

## 🏗️ Architecture

```
┌──────────────┐     ┌─────────────────────────┐     ┌──────────────┐     ┌──────────────┐     ┌───────────┐
│  React Chat  │────▶│  FastAPI Agent Backend   │────▶│  MCP Server  │────▶│ API Gateway  │────▶│ Midterm   │
│  Frontend    │◀────│  + Ollama LLM            │◀────│  (FastMCP)   │◀────│ (Spring GW)  │◀────│   APIs    │
│  :5173       │     │  + MCP Client            │     │  stdio       │     │  :8081 (EC2) │     │  :8080    │
└──────────────┘     │  :8000                   │     └──────────────┘     └──────────────┘     └───────────┘
                     └─────────────────────────┘
```

### Components

| Component | Technology | Port |
|-----------|-----------|------|
| **Frontend** | React + Vite | 5173 |
| **Agent Backend** | Python FastAPI | 8000 |
| **LLM** | Ollama (llama3.1) | 11434 |
| **MCP Server** | Python FastMCP (stdio) | — |
| **API Gateway** | Spring Cloud Gateway | 8081 |
| **Midterm APIs** | Spring Boot | 8080 |
| **Database** | PostgreSQL (AWS RDS) | 5432 |

### Flow

1. User types a message in the React chat UI
2. Frontend sends POST to FastAPI backend (`/chat`)
3. Backend forwards message + conversation history to Ollama LLM
4. Ollama decides which MCP tool to call (or responds conversationally)
5. If tool call → MCP Client executes the tool via the MCP Server
6. MCP Server routes the request through the **API Gateway**
7. Gateway proxies to the Midterm Spring Boot API
8. Response flows back through the chain to the frontend

---

## 🛠️ Tech Stack

- **Frontend:** React 19, Vite 8, CSS3 (dark theme, glassmorphism)
- **Backend:** Python 3.9+, FastAPI, Uvicorn
- **LLM:** Ollama (local) with llama3.1 model
- **MCP:** FastMCP (Model Context Protocol SDK)
- **Gateway:** Spring Cloud Gateway MVC
- **APIs:** Spring Boot 3 + Spring Security (JWT)
- **Database:** PostgreSQL on AWS RDS

---

## 🚀 Setup & Run

### Prerequisites

- Python 3.9+
- Node.js 18+
- [Ollama](https://ollama.com/download) installed

### 1. Install Ollama & Pull Model

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama service
ollama serve

# Pull the model (in another terminal)
ollama pull llama3.1
```

### 2. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Configure environment (edit .env if needed)
# GATEWAY_URL=http://16.171.162.201:8081/api/v1

# Run the agent backend
python main.py
```

Backend will start on `http://127.0.0.1:8000`

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend will start on `http://localhost:5173`

### 4. (Optional) Test MCP Server Standalone

```bash
mcp dev mcp_server.py
```

---

## 📁 Project Structure

```
airline-ai-agent/
├── .env                    # Environment config (Gateway URL, auth)
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── main.py                 # FastAPI Agent Backend + MCP Client
├── mcp_server.py           # MCP Server — airline API tools
└── frontend/
    ├── package.json
    ├── index.html
    ├── vite.config.js
    └── src/
        ├── main.jsx
        ├── index.css       # Global styles, dark theme
        ├── App.css         # Component styles
        └── App.jsx         # React Chat UI
```

---

## 🎯 Features

### MCP Tools Available

| Tool | Description | API Endpoint | Auth |
|------|-------------|-------------|------|
| `search_flights` | Search flights between airports | `GET /flights/search` | Public |
| `book_flight` | Purchase a ticket | `POST /tickets/buy` | JWT |
| `check_in` | Perform check-in | `POST /tickets/checkin` | Public |
| `get_ticket` | View ticket details | `GET /tickets/{id}` | Public |
| `cancel_ticket` | Cancel a ticket | `DELETE /tickets/cancel/{id}` | JWT |

### Chat Capabilities

- Natural language flight search ("Find flights from Istanbul to Frankfurt")
- Ticket booking with AI-extracted parameters
- Check-in assistance
- Ticket lookup and cancellation
- Conversational memory (multi-turn context)

### UI Features

- Dark mode aviation theme
- Glassmorphism effects
- Flight result cards
- Status badges (success/error)
- Typing indicators
- Conversation sidebar with history
- Auto-persisted conversations (localStorage)
- Responsive design

---

## 📐 Design Decisions & Assumptions

1. **Local LLM:** Using Ollama with llama3.1 for tool-calling capability. No cloud API keys required.
2. **MCP Architecture:** MCP Server defines tools that map to Gateway endpoints. The agent backend acts as MCP Client.
3. **Auth:** Uses hardcoded admin/password for JWT authentication. Token is cached during the session.
4. **Gateway Routing:** All API calls go through the Spring Cloud Gateway (port 8081), which proxies to the backend (port 8080).
5. **Conversation History:** Stored in-memory on the backend (last 20 messages sent to LLM for context). Frontend persists to localStorage.

---

## ⚠️ Known Issues

1. Ollama must be running locally (`ollama serve`) before starting the backend
2. First LLM response may take a few seconds as the model loads into memory
3. Gateway/EC2 must be running for API calls to work
4. JWT token expires — restart backend to re-authenticate if needed

---

## 🔗 Links

- **Source Code:** [GitHub Repository](https://github.com/uneregemen/airlineAgent)
- **Midterm API Swagger:** `http://16.171.162.201:8080/swagger-ui/index.html`
- **API Gateway:** `http://16.171.162.201:8081`

---

## 👤 Author

**Egemen Üner** — SE4458 Software Architecture
