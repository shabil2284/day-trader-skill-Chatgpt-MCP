import asyncio
import traceback

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def test_mcp(url):
    print("\n" + "=" * 70)
    print(f"Testing MCP server: {url}")
    print("=" * 70)

    try:
        async with streamablehttp_client(url) as (
            read_stream,
            write_stream,
            get_session_id,
        ):
            print("HTTP connection established.")

            async with ClientSession(
                read_stream,
                write_stream
            ) as session:

                print("Sending MCP initialize request...")

                result = await session.initialize()

                print("\nSUCCESS: MCP initialization completed.")
                print("Server information:", result.serverInfo)
                print("Protocol version:", result.protocolVersion)

                return True

    except BaseException as error:
        print("\nFAILED: MCP initialization did not complete.")
        print("\nFull exception traceback:")

        traceback.print_exception(
            type(error),
            error,
            error.__traceback__,
            chain=True,
        )

        if isinstance(error, BaseExceptionGroup):
            print("\nNested exceptions:")

            for index, nested_error in enumerate(
                error.exceptions, start=1
            ):
                print(f"\nNested error {index}:")
                traceback.print_exception(nested_error)

        return False


async def main():
    results = {}

    servers = [
        ("Analysis MCP", "http://analysis-mcp:8000/mcp"),
        ("Execution MCP", "http://execution-mcp:8001/mcp"),
    ]

    for name, url in servers:
        results[name] = await test_mcp(url)

    print("\n" + "=" * 70)
    print("FINAL TEST SUMMARY")
    print("=" * 70)

    for name, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f"{name}: {status}")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
