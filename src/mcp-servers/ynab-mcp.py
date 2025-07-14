"""
YNAB MCP Server - Provides access to YNAB budget data via MCP protocol
"""

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
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    if name == "get_account_balances":
        try:
            # Fetch accounts
            url_accounts = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}/accounts"
            response_accounts = requests.get(url_accounts, headers=headers)
            response_accounts.raise_for_status()
            data_accounts = response_accounts.json()

            accounts = data_accounts["data"]["accounts"]

            # Fetch currency code from budget summary
            url_budget = f"{BASE_URL}/budgets/{YNAB_BUDGET_ID}"
            response_budget = requests.get(url_budget, headers=headers)
            response_budget.raise_for_status()
            data_budget = response_budget.json()
            currency_code = (
                data_budget["data"]["budget"]
                .get("currency_format", {})
                .get("iso_code", "USD")
            )

            result = "💰 **YNAB Account Balances:**\n\n"

            total_balance = 0
            for account in accounts:
                if not account.get("closed", False):  # Only show open accounts
                    balance = account["balance"] / 1000  # YNAB stores in milliunits
                    total_balance += balance
                    result += (
                        f"• **{account['name']}**: {balance:,.2f} {currency_code}\n"
                    )

            result += f"\n**Total Balance**: {total_balance:,.2f} {currency_code}"

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
