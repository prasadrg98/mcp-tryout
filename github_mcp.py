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
           "filesystem": {
               "command": "npx",
               "args": [
                   "-y",
                   "@modelcontextprotocol/server-filesystem",
                   "/Users/rgrg/Desktop/educosys"
               ],
               "transport":"stdio"
           }
       }
   )
   llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
   tools = await client.get_tools()
   agent = create_react_agent(llm, tools)

   ################# For grok #################
#    agent = create_react_agent("groq:llama-3.3-70b-versatile", tools)
#    response = await agent.ainvoke({
    #   "messages": [{"role": "user", "content": "update file test.txt in repository prasadrg98/sample in master branch with content \
    #                                 of binary search code in python"}]
    # })
   #    response = await agent.ainvoke({"messages": "what are the files present in repository prasadrg98/sample"})



   # Local File System MCP
   response = await agent.ainvoke(
         {"messages": "create or ensure directory 'DS' exists in /Users/rgrg/Desktop/educosys and create a file test.txt with 'Hello World'"
        }
      )
   print(response["messages"][-1].content)

if __name__ == "__main__":
   asyncio.run(run_agent())

