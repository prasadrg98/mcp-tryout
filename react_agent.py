from dotenv import load_dotenv
load_dotenv()


from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

# ChatGPT Plus: Uses hierarchical summarization for long conversations
# Claude: Implements smart truncation with context preservation
# Enterprise chatbots: Often use sliding windows with daily summaries
# Customer support: Keeps recent messages + summary of case history
checkpoint_saver = InMemorySaver() #Can be switched to a persistent saver like Chroma or Pinecone

def display_graph():
    try:
        img = agent.get_graph().draw_mermaid_png()
        with open("react_graph.png", "wb") as f:
            f.write(img)
    except Exception as e:
        print(f"Could not display graph: {e}")

agent = create_react_agent(
   model="groq:llama-3.3-70b-versatile", 
   tools=[],
   checkpointer=checkpoint_saver,
   prompt="You are a helpful assistant"
)

display_graph()
config = {"configurable": {"thread_id": "1"}}
# Run the agents
response = agent.invoke(
   {"messages": [{"role": "user", "content": "who is MSD?"}]}, config=config
)

config = {"configurable": {"thread_id": "1"}}
response = agent.invoke(
    {"messages": [{"role": "user", "content": "when was he born?"}]}, config=config
)

print("=== Messages in Response ===")
for i, message in enumerate(response['messages']):
    print(f"\nMessage {i + 1}:")
    print(f"Type: {type(message).__name__}")
    print(f"Role: {getattr(message, 'type', 'N/A')}")
    print(f"Content: {message.content}")
    if hasattr(message, 'id'):
        print(f"ID: {message.id}")
    print("-" * 50)


from langgraph.checkpoint.memory import InMemorySaver
from langchain.chat_models import init_chat_model

class SummarizingCheckpointer(InMemorySaver):
    def __init__(self, max_messages=10):
        super().__init__()
        self.max_messages = max_messages
        self.model = init_chat_model("groq:llama-3.3-70b-versatile")
    
    def get(self, config):
        checkpoint = super().get(config)
        if checkpoint and len(checkpoint.channel_values.get('messages', [])) > self.max_messages:
            messages = checkpoint.channel_values['messages']
            
            # Keep recent messages + create summary of older ones
            recent_messages = messages[-5:]  # Keep last 5 messages
            old_messages = messages[:-5]     # Summarize older messages
            
            # Create summary
            summary_prompt = f"Summarize this conversation history: {[msg.content for msg in old_messages]}"
            summary = self.model.invoke([{"role": "user", "content": summary_prompt}])
            
            # Replace old messages with summary
            summary_message = {"role": "system", "content": f"Previous conversation summary: {summary.content}"}
            checkpoint.channel_values['messages'] = [summary_message] + recent_messages
            
        return checkpoint

# Usage
summarizing_saver = SummarizingCheckpointer(max_messages=10)
# agent = create_react_agent(
#     model="groq:llama-3.3-70b-versatile",
#     tools=[],
#     checkpointer=summarizing_saver
# )

# 1. Conversation Summarization
# 2. Sliding Window Context
# 3. Hierarchical Memory
# 4. Token-Aware Truncation
# 5. Semantic Compression



