"""
Airline MCP Server — Model Context Protocol Server for Airline APIs.

This module implements an MCP-style tool server that exposes airline API
operations as callable tools. Each tool maps to a Gateway API endpoint.

Architecture:
  MCP Server (this file) → API Gateway (Spring Cloud) → Midterm APIs (Spring Boot)

Tools:
  - search_flights: Search available flights between airports
  - book_flight: Purchase a ticket for a specific flight
  - check_in: Perform check-in for a booked flight
  - get_ticket: View ticket details by PNR/ID
  - cancel_ticket: Cancel an existing ticket
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://16.171.162.201:8081/api/v1")
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "password")

# --- JWT Token Cache ---
_jwt_token = None


def get_jwt_token():
    """Authenticate with the airline API and cache a JWT token."""
    global _jwt_token
    if _jwt_token:
        return _jwt_token

    try:
        res = requests.post(
            "{}/auth/login".format(GATEWAY_URL),
            json={"username": AUTH_USERNAME, "password": AUTH_PASSWORD},
            timeout=10,
        )
        res.raise_for_status()
        data = res.json()
        if data.get("status") == "Success":
            _jwt_token = data.get("message", "")
            return _jwt_token
        return ""
    except Exception as e:
        print("[MCP Server] Auth error: {}".format(e))
        return ""


def auth_headers():
    """Return HTTP headers with JWT Authorization."""
    token = get_jwt_token()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer {}".format(token)
    return headers


# ═══════════════════════════════════════════════════════════
# MCP TOOLS — Each function is an MCP tool mapped to an API
# ═══════════════════════════════════════════════════════════


def search_flights(departure_airport, arrival_airport, date=None, number_of_people=1):
    """
    MCP Tool: Search for available flights between two airports.

    Args:
        departure_airport (str): IATA code of departure airport (e.g., IST)
        arrival_airport (str): IATA code of arrival airport (e.g., FRA)
        date (str, optional): Flight date in YYYY-MM-DD format
        number_of_people (int): Number of passengers (default: 1)

    Gateway Endpoint: GET /api/v1/flights/search
    Auth: Public (no JWT required)
    """
    if not date:
        date = "2025-01-01"

    params = {
        "airportFrom": departure_airport.upper(),
        "airportTo": arrival_airport.upper(),
        "dateFrom": date,
        "dateTo": "2027-12-31",
        "numberOfPeople": number_of_people,
        "isRoundTrip": False,
        "pageNumber": 1,
        "pageSize": 10,
    }

    try:
        res = requests.get(
            "{}/flights/search".format(GATEWAY_URL),
            params=params,
            timeout=15,
        )
        res.raise_for_status()
        data = res.json()
        flights = data.get("content", [])

        if not flights:
            return json.dumps({
                "status": "no_results",
                "message": "No flights found from {} to {}.".format(
                    departure_airport.upper(), arrival_airport.upper()
                ),
            })

        result = []
        for f in flights:
            result.append({
                "flightNumber": f.get("flightNumber", "N/A"),
                "from": f.get("airportFrom", "N/A"),
                "to": f.get("airportTo", "N/A"),
                "departure": f.get("dateFrom", "N/A"),
                "arrival": f.get("dateTo", "N/A"),
                "availableSeats": f.get("availableSeats", 0),
            })

        return json.dumps({
            "status": "success",
            "count": len(result),
            "flights": result,
        })

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def book_flight(flight_number, date, passenger_name):
    """
    MCP Tool: Book/purchase a ticket for a specific flight.

    Args:
        flight_number (str): The flight number to book (e.g., TK1523)
        date (str): The flight date in YYYY-MM-DD format
        passenger_name (str): Full name of the passenger

    Gateway Endpoint: POST /api/v1/tickets/buy
    Auth: JWT required
    """
    payload = {
        "flightNumber": flight_number.upper(),
        "date": date,
        "passengerName": passenger_name,
    }

    try:
        res = requests.post(
            "{}/tickets/buy".format(GATEWAY_URL),
            json=payload,
            headers=auth_headers(),
            timeout=15,
        )
        res.raise_for_status()
        data = res.json()

        return json.dumps({
            "status": data.get("status", "Unknown"),
            "message": data.get("message", ""),
            "flight_number": flight_number.upper(),
            "passenger": passenger_name,
            "date": date,
        })

    except requests.exceptions.HTTPError as e:
        try:
            err_data = e.response.json()
            return json.dumps({
                "status": "error",
                "message": err_data.get("message", str(e)),
            })
        except Exception:
            return json.dumps({"status": "error", "message": str(e)})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def check_in(flight_number, date, passenger_name):
    """
    MCP Tool: Perform check-in for a booked flight. A seat will be assigned.

    Args:
        flight_number (str): The flight number (e.g., TK1523)
        date (str): The flight date in YYYY-MM-DD format
        passenger_name (str): Full name of the passenger (must match booking)

    Gateway Endpoint: POST /api/v1/tickets/checkin
    Auth: JWT required
    """
    payload = {
        "flightNumber": flight_number.upper(),
        "date": date,
        "passengerName": passenger_name,
    }

    try:
        res = requests.post(
            "{}/tickets/checkin".format(GATEWAY_URL),
            json=payload,
            headers=auth_headers(),
            timeout=15,
        )
        res.raise_for_status()
        data = res.json()

        return json.dumps({
            "status": data.get("status", "Unknown"),
            "message": data.get("message", ""),
            "flight_number": flight_number.upper(),
            "passenger": passenger_name,
        })

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else 0
        try:
            err_data = e.response.json()
            return json.dumps({
                "status": "error",
                "message": err_data.get("message", str(e)),
            })
        except Exception:
            body = ""
            try:
                body = e.response.text[:300]
            except Exception:
                pass
            return json.dumps({
                "status": "error",
                "message": "HTTP {} from backend. {}".format(status_code, body or str(e)),
            })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def get_ticket(ticket_id):
    """
    MCP Tool: Get details of a specific ticket by its ID (PNR number).

    Args:
        ticket_id (int): The ticket/PNR ID number

    Gateway Endpoint: GET /api/v1/tickets/{id}
    Auth: Public (no JWT required)
    """
    try:
        res = requests.get(
            "{}/tickets/{}".format(GATEWAY_URL, ticket_id),
            timeout=15,
        )
        res.raise_for_status()
        data = res.json()

        return json.dumps({
            "status": "success",
            "ticket": {
                "id": data.get("id"),
                "passengerName": data.get("passengerName"),
                "flightNumber": data.get("flightNumber"),
                "purchaseDate": data.get("purchaseDate"),
            },
        })

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def cancel_ticket(ticket_id):
    """
    MCP Tool: Cancel an existing ticket by its ID.

    Args:
        ticket_id (int): The ticket/PNR ID number to cancel

    Gateway Endpoint: DELETE /api/v1/tickets/cancel/{id}
    Auth: JWT required
    """
    try:
        res = requests.delete(
            "{}/tickets/cancel/{}".format(GATEWAY_URL, ticket_id),
            headers=auth_headers(),
            timeout=15,
        )
        res.raise_for_status()
        data = res.json()

        return json.dumps({
            "status": data.get("status", "Unknown"),
            "message": data.get("message", ""),
        })

    except requests.exceptions.HTTPError as e:
        try:
            err_data = e.response.json()
            return json.dumps({
                "status": "error",
                "message": err_data.get("message", str(e)),
            })
        except Exception:
            return json.dumps({"status": "error", "message": str(e)})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# --- MCP Tool Registry ---
# Maps tool names to their handler functions
MCP_TOOLS = {
    "search_flights": search_flights,
    "book_flight": book_flight,
    "check_in": check_in,
    "get_ticket": get_ticket,
    "cancel_ticket": cancel_ticket,
}


def execute_tool(tool_name, arguments):
    """
    MCP Tool Executor — Routes a tool call to the appropriate handler.

    Args:
        tool_name (str): Name of the MCP tool to execute
        arguments (dict): Arguments for the tool

    Returns:
        str: JSON string with the tool result
    """
    handler = MCP_TOOLS.get(tool_name)
    if not handler:
        return json.dumps({"status": "error", "message": "Unknown tool: {}".format(tool_name)})

    try:
        return handler(**arguments)
    except TypeError as e:
        return json.dumps({"status": "error", "message": "Invalid arguments: {}".format(str(e))})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# --- Standalone Test ---
if __name__ == "__main__":
    print("=== Airline MCP Server — Standalone Test ===")
    print("Gateway: {}".format(GATEWAY_URL))
    print()

    # Test: Search flights
    print("1. Testing search_flights(IST, FRA)...")
    result = search_flights("IST", "FRA")
    print("   Result: {}".format(result[:200]))
    print()

    # Test: Execute tool via registry
    print("2. Testing execute_tool('search_flights', ...)...")
    result = execute_tool("search_flights", {
        "departure_airport": "IST",
        "arrival_airport": "JFK",
    })
    print("   Result: {}".format(result[:200]))
    print()

    print("=== All tests complete ===")
