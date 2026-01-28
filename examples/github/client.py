# client.py
import asyncio
import json
import os
from dotenv import load_dotenv

from agentdna import AgentDNA
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

async def main():
    dna = AgentDNA(alias="github_cli_host", role="host", api_key=os.environ["AGENTDNA_API_KEY"])

    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env=dict(os.environ),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            host_msg = {
                "tool": "create_issue",
                "args": {
                    "title": "CLI test issue",
                    "description": "Created via GitHub MCP CLI",
                },
            }

            built = dna.build(original_message=json.dumps(host_msg))
            result = await session.call_tool(
                "create_issue",
                {
                    **host_msg["args"],
                    "dna_envelope": built["host_json"],
                },
            )

            print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())
