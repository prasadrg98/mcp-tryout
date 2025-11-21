import os
import logging
import pkgutil
import asyncio
import streamlit as st
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

# Suppress logs
for module_info in pkgutil.iter_modules():
    logging.getLogger(module_info.name).setLevel(logging.ERROR)

load_dotenv()

# Streamlit page config
st.set_page_config(
    page_title="Educosys Discord Chatbot",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Educosys Discord Chatbot")
st.markdown("Chat with the bot and messages will also be sent to Discord!")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = None

if "client" not in st.session_state:
    st.session_state.client = None

# Initialize MCP client and agent
@st.cache_resource
def initialize_agent():
    """Initialize the MCP client and agent"""
    try:
        # Create MCP client with Discord and local filesystem tools
        client = MultiServerMCPClient({
            "discord": {
                "command": "python3",
                "args": ["discord_msg_server.py"],
                "transport": "stdio"
            },
            "localfilesystem": {
                "command": "python3", 
                "args": ["local_file_mcp_server.py"],
                "transport": "stdio"
            }
        })
        
        return client
    except Exception as e:
        st.error(f"Failed to initialize MCP client: {e}")
        return None

async def setup_agent():
    """Setup the agent with tools"""
    if st.session_state.client is None:
        st.session_state.client = initialize_agent()
    
    if st.session_state.client and st.session_state.agent is None:
        try:
            # Get tools from MCP servers
            tools = await st.session_state.client.get_tools()
            
            # Initialize LLM and agent
            checkpointer = InMemorySaver()
            llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
            
            agent = create_react_agent(
                llm, 
                tools=tools, 
                checkpointer=checkpointer,
                prompt="You are a helpful assistant with access to Discord messaging and file operations. When users ask to send messages, use the Discord tools to send them."
            )
            
            st.session_state.agent = agent
            st.success("✅ Agent initialized with Discord and file system tools!")
            
            # Show available tools
            with st.expander("🔧 Available Tools"):
                for tool in tools:
                    st.write(f"**{tool.name}**: {tool.description}")
                    
        except Exception as e:
            st.error(f"Failed to setup agent: {e}")

async def get_agent_response(user_input: str):
    """Get response from agent and handle Discord integration"""
    if st.session_state.agent is None:
        return "❌ Agent not initialized. Please refresh the page."
    
    try:
        # Configure thread for conversation history
        config = {"configurable": {"thread_id": "streamlit_session"}}
        
        # Get response from agent
        response = await st.session_state.agent.ainvoke({
            "messages": [{"role": "user", "content": user_input}]
        }, config)
        
        return response["messages"][-1].content
        
    except Exception as e:
        return f"❌ Error getting response: {str(e)}"

def stream_graph_updates(user_input: str):
    """Stream updates from the agent"""
    assistant_response = ""
    
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # Run async function
            response = asyncio.run(get_agent_response(user_input))
            assistant_response = response
            message_placeholder.markdown(assistant_response)
            
        except Exception as e:
            assistant_response = f"❌ Error: {str(e)}"
            message_placeholder.markdown(assistant_response)
    
    # Add to session state
    st.session_state.messages.append(("assistant", assistant_response))
    return assistant_response

# Initialize agent on app start
if st.session_state.agent is None:
    with st.spinner("🔄 Initializing Discord chatbot..."):
        asyncio.run(setup_agent())

# Sidebar with options
with st.sidebar:
    st.header("🎛️ Controls")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()
    
    # Discord commands examples
    st.header("💬 Discord Commands")
    st.markdown("""
    **Examples you can try:**
    
    - Send a simple message:
      `Send a Discord message "Hello from Streamlit!"`
    
    - Send an embed:
      `Send an embed with title 'Update' and description 'Bot is working!'`
    
    - Read Discord messages:
      `Read the last 5 messages from Discord and summarize them`
    
    - File operations:
      `Create a file called test.txt with content "Hello World"`
    """)

# Display chat history
for role, message in st.session_state.messages:
    with st.chat_message(role):
        st.markdown(message)

# Chat input
if prompt := st.chat_input("💬 Type your message here..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Add user message to session state
    st.session_state.messages.append(("user", prompt))
    
    # Get and display bot response
    with st.spinner("🤖 Thinking..."):
        response = stream_graph_updates(prompt)

# Add some helpful information at the bottom
with st.expander("ℹ️ How to use"):
    st.markdown("""
    ### How to use this Discord Chatbot:
    
    1. **Regular Chat**: Ask any question and the bot will respond
    2. **Discord Integration**: Ask the bot to send messages to Discord
    3. **File Operations**: Request file creation, reading, or management
    4. **Discord Reading**: Ask to read and summarize Discord messages
    
    ### Example Commands:
    - `Send a Discord message saying "Hello from the bot!"`
    - `Create a new file called notes.txt`
    - `Read the latest Discord messages and tell me what's happening`
    - `Send an embed to Discord with today's updates`
    
    The bot has access to both Discord messaging and local file system operations!
    """)
