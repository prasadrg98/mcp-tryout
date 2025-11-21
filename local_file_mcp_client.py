import os
import logging
import pkgutil

for module_info in pkgutil.iter_modules():
    # print("Disabling logs for module:", module_info.name)
    logging.getLogger(module_info.name).setLevel(logging.ERROR)
from dotenv import load_dotenv
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model

async def run_agent():
    client = MultiServerMCPClient(
        {
            "localfilesystem": {
                "command" : "python3",
                "args": [
                    "local_file_mcp_server.py",
                    # "/Users/rgrg/Desktop"
                ],
                "transport":"stdio"
            },
            "github": {
               "command": "npx",
               "args": [
                   "-y",
                   "@modelcontextprotocol/server-github"
               ],
               "env": {
                   "GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_TOKEN
               },
               "transport": "stdio"
           },
        #    "filesystem": {
        #        "command": "npx",
        #        "args": [
        #            "-y",
        #            "@modelcontextprotocol/server-filesystem",
        #            "/Users/rgrg/Desktop/educosys"
        #        ],
        #        "transport": "stdio"
        #    }
        }
    )

    llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
    tools = await client.get_tools()
    agent = create_react_agent(llm, tools)
    # img = agent.get_graph().draw_mermaid_png()
    # with open("agent_graph.png", "wb") as f:
    #     f.write(img)



    # print("=== Available Tools ===")
    # for tool in tools:
    #     print(f"Tool: {tool.name}")
    #     print(f"Description: {tool.description}")
    #     print(f"Server: {getattr(tool, '_server_name', 'unknown')}")
    #     print("-" * 40)


    response = await agent.ainvoke({
    #    "messages": [{"role": "user", "content": "create a new file / update the file test1.txt if exists with content Hello World"}]
    "messages": [{"role": "user", "content": "Read the files in the directory and summarize what is the project about"}]
    #    "messages": [{
    #        'role': 'user',
    #         'content': "Delete the file test1.txt if it exists"
    #    }]
    })
    print(response["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(run_agent())
