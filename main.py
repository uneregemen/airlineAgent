"""
Airline AI Agent Backend — FastAPI + Ollama LLM + MCP Client.

This is the Agent Backend that:
1. Receives chat messages from the React frontend
2. Sends messages + conversation history to Ollama LLM
3. LLM decides which MCP tool to call (or responds conversationally)
4. Executes tool calls via the MCP Server (mcp_server.py)
5. Returns results back to the frontend

Architecture:
  Frontend → Agent Backend (this) → Ollama LLM
                                  → MCP Server → API Gateway → Midterm APIs
"""

import uvicorn
import json
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import ollama

# Import MCP Server tools
from mcp_server import execute_tool

load_dotenv()

# --- Configuration ---
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://16.171.162.201:8081/api/v1")

# --- In-Memory Conversation Store ---
conversations = {}

# --- MCP Tool Definitions for Ollama ---
# These are the tool schemas that Ollama uses to decide which tool to call.
# The actual execution is handled by the MCP Server (mcp_server.py).
OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search for available flights between two airports. Use IATA airport codes like IST (Istanbul), FRA (Frankfurt), JFK (New York), LHR (London), CDG (Paris), SAW (Sabiha Gokcen), ESB (Ankara), ADB (Izmir), AYT (Antalya).",
            "parameters": {
                "type": "object",
                "properties": {
                    "departure_airport": {
                        "type": "string",
                        "description": "IATA code of the departure airport (e.g., IST)",
                    },
                    "arrival_airport": {
                        "type": "string",
                        "description": "IATA code of the arrival airport (e.g., FRA)",
                    },
                    "date": {
                        "type": "string",
                        "description": "Flight date in YYYY-MM-DD format. Optional.",
                    },
                    "number_of_people": {
                        "type": "integer",
                        "description": "Number of passengers. Default is 1.",
                    },
                },
                "required": ["departure_airport", "arrival_airport"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_flight",
            "description": "Book/purchase a ticket for a specific flight. Requires flight number, date, and passenger name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_number": {
                        "type": "string",
                        "description": "The flight number to book (e.g., TK1523)",
                    },
                    "date": {
                        "type": "string",
                        "description": "The flight date in YYYY-MM-DD format",
                    },
                    "passenger_name": {
                        "type": "string",
                        "description": "Full name of the passenger",
                    },
                },
                "required": ["flight_number", "date", "passenger_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_in",
            "description": "Perform check-in for a booked flight. Requires flight number, date, and passenger name. A seat number will be assigned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_number": {
                        "type": "string",
                        "description": "The flight number (e.g., TK1523)",
                    },
                    "date": {
                        "type": "string",
                        "description": "The flight date in YYYY-MM-DD format",
                    },
                    "passenger_name": {
                        "type": "string",
                        "description": "Full name of the passenger (must match booking)",
                    },
                },
                "required": ["flight_number", "date", "passenger_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticket",
            "description": "Get details of a specific ticket by its ID/PNR number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "integer",
                        "description": "The ticket/PNR ID number",
                    },
                },
                "required": ["ticket_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_ticket",
            "description": "Cancel an existing ticket by its ID/PNR number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "integer",
                        "description": "The ticket/PNR ID number to cancel",
                    },
                },
                "required": ["ticket_id"],
            },
        },
    },
]

# --- System Prompt ---
SYSTEM_PROMPT = """You are SkyAgent AI, an intelligent airline flight assistant. You help users with:

1. **Searching flights** — Find available flights between airports using IATA codes
2. **Booking flights** — Purchase tickets for specific flights
3. **Check-in** — Perform check-in for booked flights
4. **Ticket details** — Look up ticket information by PNR/ID
5. **Cancel tickets** — Cancel existing bookings

Rules:
- Always use IATA airport codes (IST, FRA, JFK, LHR, CDG, SAW, ESB, ADB, AYT, etc.)
- When the user wants to book, you need: flight_number, date (YYYY-MM-DD), passenger_name
- When the user wants to check in, you need: flight_number, date, passenger_name
- If the user doesn't provide a date, ask for it or use a reasonable default
- Present flight results clearly with flight numbers, routes, times, and available seats
- Be friendly, professional, and concise
- If the user is just chatting or saying hello, respond conversationally without calling tools
- Always confirm actions with the user before executing (e.g., "I'll book flight TK1523 for you...")
"""

# --- FastAPI App ---
app = FastAPI(title="Airline AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat")
async def chat(request: Request):
    """
    Main chat endpoint.

    Flow:
    1. Receive user message from React frontend
    2. Build conversation context (system prompt + history + new message)
    3. Send to Ollama LLM with available MCP tool definitions
    4. If LLM decides to call a tool → execute via MCP Server
    5. Send tool results back to LLM for natural language response
    6. Return final response to frontend
    """
    data = await request.json()
    user_msg = data.get("message", "")
    conversation_id = data.get("conversation_id", "default")

    print("\n" + "=" * 60)
    print("[Chat] User ({}): {}".format(conversation_id, user_msg))

    # Get or create conversation history
    if conversation_id not in conversations:
        conversations[conversation_id] = []

    history = conversations[conversation_id]

    # Build messages for Ollama (system + last 20 history + new message)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-20:])
    messages.append({"role": "user", "content": user_msg})

    try:
        # ── Step 1: Send to Ollama with MCP tool definitions ──
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            tools=OLLAMA_TOOLS,
        )

        # ollama SDK returns Pydantic objects — use attribute access, not .get()
        message = response.message

        # ── Step 2: Check if LLM wants to call MCP tools ──
        if message.tool_calls:
            tool_results = []

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args = tool_call.function.arguments

                print("  [LLM → MCP] Tool call: {}({})".format(func_name, func_args))

                # ── Step 3: Execute tool via MCP Server ──
                result = execute_tool(func_name, func_args)
                tool_results.append({
                    "tool": func_name,
                    "result": result,
                })

                print("  [MCP → Gateway] Result: {}...".format(result[:200]))

            # ── Step 4: Send tool results back to LLM ──
            # Rebuild assistant message as a plain dict so ollama can serialize it
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in message.tool_calls
                ],
            })

            for tr in tool_results:
                messages.append({
                    "role": "tool",
                    "content": tr["result"],
                })

            # Get final natural language response from LLM
            final_response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=messages,
            )

            final_text = (
                final_response.message.content
                or "I processed your request but couldn't generate a response."
            )

            # Save to conversation history
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": final_text})

            # Parse tool results for structured frontend data
            structured_data = []
            for tr in tool_results:
                try:
                    parsed = json.loads(tr["result"])
                    parsed["_tool"] = tr["tool"]
                    structured_data.append(parsed)
                except (json.JSONDecodeError, ValueError):
                    structured_data.append({"_tool": tr["tool"], "raw": tr["result"]})

            print("  [Response] {}...".format(final_text[:150]))

            return {
                "response": final_text,
                "tool_calls": structured_data,
                "conversation_id": conversation_id,
            }

        else:
            # ── No tool calls — conversational response ──
            assistant_text = (
                message.content or "I didn't understand that. Could you rephrase?"
            )

            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": assistant_text})

            print("  [Response] {}...".format(assistant_text[:150]))

            return {
                "response": assistant_text,
                "tool_calls": [],
                "conversation_id": conversation_id,
            }

    except Exception as e:
        print("  [Error] {}".format(e))
        import traceback
        traceback.print_exc()
        return {
            "response": "Sorry, I encountered an error: {}".format(str(e)),
            "tool_calls": [],
            "conversation_id": conversation_id,
        }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "model": OLLAMA_MODEL, "gateway": GATEWAY_URL}


@app.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear conversation history for a specific conversation."""
    if conversation_id in conversations:
        del conversations[conversation_id]
    return {"status": "cleared"}


if __name__ == "__main__":
    print("=" * 60)
    print("  SkyAgent AI — Airline Flight Assistant")
    print("=" * 60)
    print("  LLM Model:  {}".format(OLLAMA_MODEL))
    print("  Gateway:     {}".format(GATEWAY_URL))
    print("  Server:      http://127.0.0.1:8000")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000)