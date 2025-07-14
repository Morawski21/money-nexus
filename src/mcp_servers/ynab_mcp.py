import os
import asyncio
import requests
from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

# Load environment variables from .env
load_dotenv()

YNAB_TOKEN = os.getenv("YNAB_TOKEN")
YNAB_BUDGET_ID = os.getenv("YNAB_BUDGET_ID")
BASE_URL = "https://api.youneedabudget.com/v1"

if not YNAB_TOKEN or not YNAB_BUDGET_ID:
    raise ValueError("YNAB_TOKEN and YNAB_BUDGET_ID must be set in .env file")

headers = {"Authorization": f"Bearer {YNAB_TOKEN}"}

# Create the MCP server
server = Server("ynab-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available YNAB tools"""
    return [
        Tool(
            name="get_account_balances",
            description="Get account balances from YNAB budget",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_budget_summary",
            description="Get budget name and basic info",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_income_for_period",
            description="Get all true income transactions (not transfers) for the last N months (default 3). Argument: months (int, optional, default 3)",
            inputSchema={
                "type": "object",
                "properties": {
                    "months": {"type": "integer", "minimum": 1, "default": 3}
                },
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    if name == "get_account_balances":
        try:
            url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/accounts"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            accounts = data["data"]["accounts"]
            result = "💰 **YNAB Account Balances:**\n\n"

            total_balance = 0
            for account in accounts:
                if not account.get("closed", False):  # Only show open accounts
                    balance = account["balance"] / 1000  # YNAB stores in milliunits
                    total_balance += balance
                    result += f"• **{account['name']}**: ${balance:,.2f}\n"

            result += f"\n**Total Balance**: ${total_balance:,.2f}"

            return [TextContent(type="text", text=result)]

        except Exception as e:
            return [
                TextContent(
                    type="text", text=f"Error fetching account balances: {str(e)}"
                )
            ]

    elif name == "get_budget_summary":
        try:
            url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            budget = data["data"]["budget"]
            result = f"📊 **Budget: {budget['name']}**\n"
            result += f"Last Modified: {budget['last_modified_on']}\n"
            result += (
                f"Currency: {budget.get('currency_format', {}).get('iso_code', 'USD')}"
            )

            return [TextContent(type="text", text=result)]

        except Exception as e:
            return [
                TextContent(type="text", text=f"Error fetching budget info: {str(e)}")
            ]

    elif name == "get_income_for_period":
        try:
            import datetime

            months = arguments.get("months", 3)
            today = datetime.date.today()
            # Calculate the first day of the period (N-1 months ago)
            year = today.year
            month = today.month - (months - 1)
            while month <= 0:
                month += 12
                year -= 1
            start_date = datetime.date(year, month, 1)
            end_date = today

            # Fetch accounts for account_id -> name mapping
            accounts_url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/accounts"
            accounts_resp = requests.get(accounts_url, headers=headers)
            accounts_resp.raise_for_status()
            accounts_data = accounts_resp.json()["data"]["accounts"]
            account_map = {a["id"]: a["name"] for a in accounts_data}

            url = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/transactions?since_date={start_date}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            transactions = response.json()["data"]["transactions"]

            total_income = 0
            lines = []
            for tx in transactions:
                tx_date = datetime.date.fromisoformat(tx["date"])
                if tx_date < start_date or tx_date > end_date:
                    continue
                if tx["amount"] > 0 and tx["category_id"] is None:
                    amount = tx["amount"] / 1000
                    payee = tx.get("payee_name", "")
                    account = account_map.get(tx.get("account_id", ""), "")
                    memo = tx.get("memo", "")
                    total_income += amount
                    lines.append(
                        f"• **{tx['date']}** | {payee} | {amount:,.2f} | {account} {('- ' + memo) if memo else ''}"
                    )

            result = f"💰 **Income Transactions (last {months} months, {start_date} to {end_date}):**\n\n"
            if lines:
                result += "\n".join(lines)
            else:
                result += "No income transactions found."
            result += f"\n\n**Total Income**: {total_income:,.2f}"

            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
