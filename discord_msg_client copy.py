import os
import logging
import pkgutil

for module_info in pkgutil.iter_modules():
    logging.getLogger(module_info.name).setLevel(logging.ERROR)
from dotenv import load_dotenv
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model

import streamlit as st
st.title("Educosys Chat App")
if "messages" not in st.session_state:
   st.session_state.messages = []

# Display previous chat history
for role, message in st.session_state.messages:
   with st.chat_message(role):
        st.markdown(message)


async def run_agent():
    client = MultiServerMCPClient(
        {
            "discord": {
                "command" : "python3",
                "args": [
                    "discord_msg_server.py",
                    # "/Users/rgrg/Desktop"
                ],
                "transport":"stdio"
            },
            "localfilesystem": {
                "command" : "python3",
                "args": [
                    "local_file_mcp_server.py",
                    # "/Users/rgrg/Desktop"
                ],
                "transport":"stdio"
            }
        }
    )

    llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
    tools = await client.get_tools()
    agent = create_react_agent(llm, tools)

    response = await agent.ainvoke({
    # "messages": [{"role": "user", "content": "Send a discord message as user Prasad with content Hello from MCP!"}]
    # "messages": [{"role": "user", "content": "Send an embed with title 'Bootcamp Demo' and description 'This is a Discord MCP test.'"}]
    # "messages": [{"role": "user", "content": "Send an embed with title 'Discord Demo' and description in code format of content of files discord_msg_server.py & discord_msg_client.py"}]
    "messages": [{"role": "user", "content": "Send a discord message 'Langgraph Simple App' and next line in code format of content of files main.py"}]
    })
    print(response["messages"][-1].content)

    print("*" * 40)

    response = await agent.ainvoke({
    "messages": [{"role": "user", "content": "Read the last 6 messages from the discord channel & summarize them in 2-3 lines."}]
    })
    print(response["messages"][-1].content)


prompt = st.chat_input("What is your question?")
if prompt:
   with st.chat_message("user"):
       st.markdown(prompt)
   st.session_state.messages.append(("user", prompt))
  

if __name__ == "__main__":
    asyncio.run(run_agent())
