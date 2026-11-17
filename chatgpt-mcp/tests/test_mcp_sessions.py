import asyncio
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ROOT = Path(__file__).resolve().parents[2]
MCP_DIR = ROOT / "chatgpt-mcp"
sys.path.insert(0, str(MCP_DIR))

import execution_server
import order_gateway
import server


class MCPServerSessions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.new_event_loop()

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()

    def check_server(self, mcp, port, expected_tools, harmless_calls, schema_checks=()):
        old_flags = (
            order_gateway.ALPACA_PAPER_TRADING_ENABLED,
            order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED,
            order_gateway.ALPACA_LIVE_TRADING_ENABLED,
            order_gateway.STATE_DIR,
        )
        with tempfile.TemporaryDirectory(prefix="dtai-mcp-session-") as state_dir:
            order_gateway.STATE_DIR = Path(state_dir)
            order_gateway.ALPACA_PAPER_TRADING_ENABLED = False
            order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED = False
            order_gateway.ALPACA_LIVE_TRADING_ENABLED = False
            app = mcp.streamable_http_app()

            async def exercise():
                async with app.router.lifespan_context(app):
                    async with httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=app), timeout=10
                    ) as http_client:
                        async with streamable_http_client(
                            f"http://127.0.0.1:{port}/mcp", http_client=http_client
                        ) as (read_stream, write_stream, _):
                            async with ClientSession(
                                read_stream, write_stream,
                                read_timeout_seconds=timedelta(seconds=10),
                            ) as session:
                                await session.initialize()
                                tools = await session.list_tools()
                                self.assertEqual(len(tools.tools), expected_tools)
                                names = {tool.name for tool in tools.tools}
                                schemas = {tool.name: tool.inputSchema for tool in tools.tools}
                                for tool_name, expected_properties in schema_checks:
                                    self.assertTrue(expected_properties.issubset(
                                        schemas[tool_name].get("properties", {})
                                    ))
                                for name, arguments, should_error in harmless_calls:
                                    result = await session.call_tool(name, arguments)
                                    self.assertEqual(result.isError, should_error, name)
                                # Exercise a later request on the same initialized session.
                                final = await session.call_tool(harmless_calls[-1][0], harmless_calls[-1][1])
                                self.assertEqual(final.isError, harmless_calls[-1][2])
                                return names

            try:
                names = self.loop.run_until_complete(exercise())
                self.assertEqual(len(names), expected_tools)
            finally:
                (
                    order_gateway.ALPACA_PAPER_TRADING_ENABLED,
                    order_gateway.ALPACA_ORDER_SUBMISSION_ENABLED,
                    order_gateway.ALPACA_LIVE_TRADING_ENABLED,
                    order_gateway.STATE_DIR,
                ) = old_flags

    def test_analysis_mcp_discovers_twenty_tools_and_keeps_session_alive(self):
        self.check_server(
            server.mcp, 19876, 20,
            [("get_account", {"mode": "paper"}, True), ("server_status", {}, False)],
            schema_checks=(
                ("backtest_strategy", {"symbol"}),
                ("propose_order", {"stop_loss_price", "take_profit_price"}),
                ("calculate_position_size", {"budget", "symbol", "entry", "stop", "target", "opening_high", "opening_low"}),
            ),
        )

    def test_execution_mcp_discovers_eleven_tools_and_keeps_session_alive(self):
        self.check_server(
            execution_server.mcp, 19877, 11,
            [("get_account", {"mode": "paper"}, True), ("get_execution_status", {}, False)],
            schema_checks=(("propose_order", {"stop_loss_price", "take_profit_price"}),),
        )


if __name__ == "__main__":
    unittest.main()
