from dotenv import load_dotenv
import os
from typing import Annotated, TypedDict
from langchain.chat_models import init_chat_model
load_dotenv()

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

# model = init_chat_model("llama-3.3-70b-versatile", model_provider="groq")
model = init_chat_model("gemini-2.5-flash", model_provider="google_genai")


def chatbot(state: State) -> State:
    return {
        "messages": [model.invoke(state["messages"])]
    }

def display_graph():
    img = graph.get_graph().draw_mermaid_png()
    with open("graph.png", "wb") as f:
        f.write(img)


def stream_graph_updates(user_input: str):
   for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
       print(f"event.values(): {len(event.values())}")
       for value in event.values(): # if multiple node & finishes at same time
           print(f"value: {value['messages']}")
           print("Assistant:", value["messages"][-1].content)


graph_builder.add_node("chatbot", chatbot, inputs=["messages"], outputs=["messages"])
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile()
display_graph()

while True:
   try:
       user_input = input("User: ")
       if user_input.lower() in ["quit", "exit", "q"]:
           print("Goodbye!")
           break
       stream_graph_updates(user_input)
   except:
       # fallback if input() is not available
       user_input = "What do you know about LangGraph? just 1 line answer"
       print("User: " + user_input)
       stream_graph_updates(user_input)
       break