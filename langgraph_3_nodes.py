from dotenv import load_dotenv
import os
from typing import Annotated, TypedDict
from langchain.chat_models import init_chat_model
load_dotenv()

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]
    analysis: Annotated[str, "A brief analysis of the conversation so far"]
    summary: Annotated[str, "A concise summary of the conversation so far"]

graph_builder = StateGraph(State)
model = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

def analyzer(state: State) -> State:
    """Analyze the sentiment / tone of the conversation so far"""
    messages_text = " ".join([msg.content for msg in state["messages"] if hasattr(msg, 'content')])
    analysis_prompt = f"Analyze the sentiment and tone of the following conversation:\n\n{messages_text}\n\nProvide a brief analysis."
    response = model.invoke([{"role": "user", "content": analysis_prompt}])
    return {
        "analysis": response.content
    }

def summarizer(state: State) -> State:
    """Summarize the conversation so far"""
    messages_text = " ".join([msg.content for msg in state["messages"] if hasattr(msg, 'content')])
    summary_prompt = f"Summarize the following conversation in a concise manner:\n\n{messages_text}\n\nProvide a concise summary."
    response = model.invoke([{"role": "user", "content": summary_prompt}])
    return {
        "summary": response.content
    }

def final_responder(state: State) -> State:
    """Generate the final response incorporating analysis and summary"""
    prompt = f"""
    Based on this analysis: {state.get('analysis', 'No analysis')}
    And this summary: {state.get('summary', 'No summary')}
    
    Provide a helpful response to the user's message: {state['messages'][-1].content}
    """
    
    response = model.invoke([{"role": "user", "content": prompt}])
    return {
        "messages": [response]
    }

def stream_graph_updates(user_input: str):
   for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
    print(f"\n--- Event with {len(event.values())} node(s) ---")
    for node_name, value in event.items():
        print(f"\nNode: {node_name}")
        print(f"Value: {value}")
        if "messages" in value and value["messages"]:
            print(f"Assistant: {value['messages'][-1].content}")

# Build the graph with parallel nodes
graph_builder.add_node("analyzer", analyzer)
graph_builder.add_node("summarizer", summarizer)
graph_builder.add_node("responder", final_responder)

# Parallel execution: both analyzer and summarizer run simultaneously
graph_builder.add_edge(START, "analyzer")
graph_builder.add_edge(START, "summarizer")

# Both feed into the final responder
graph_builder.add_edge("analyzer", "responder")
graph_builder.add_edge("summarizer", "responder")
graph_builder.add_edge("responder", END)

graph = graph_builder.compile()

def display_graph():
    img = graph.get_graph().draw_mermaid_png()
    with open("graph_3_nodes.png", "wb") as f:
        f.write(img)

display_graph()

# Test the parallel execution
if __name__ == "__main__":
    test_input = "I'm feeling really stressed about my upcoming exams and don't know how to manage my time effectively."
    print(f"User: {test_input}")
    stream_graph_updates(test_input)


# from dotenv import load_dotenv
# load_dotenv()

# from typing import Annotated, TypedDict
# from langchain.chat_models import init_chat_model
# from langgraph.graph import StateGraph, START, END
# from langgraph.graph.message import add_messages
# from langgraph.checkpoint.memory import InMemorySaver

# class State(TypedDict):
#     messages: Annotated[list, add_messages]
#     analysis_result: str
#     search_result: str
#     final_response: str

# model = init_chat_model("groq:llama-3.3-70b-versatile")
# checkpoint_saver = InMemorySaver()

# # Node 1: Analyze user input
# def analyze_input(state: State) -> State:
#     """Analyze what the user is asking for"""
#     user_message = state["messages"][-1].content
    
#     analysis_prompt = f"""
#     Analyze this user request and determine what type of response is needed:
#     User: {user_message}
    
#     Respond with one of: SEARCH, CALCULATE, GENERAL_CHAT, WEATHER
#     """
    
#     response = model.invoke([{"role": "user", "content": analysis_prompt}])
#     return {"analysis_result": response.content.strip()}

# # Node 2: Search information
# def search_node(state: State) -> State:
#     """Simulate searching for information"""
#     user_message = state["messages"][-1].content
    
#     # Simulate search (replace with real search tool)
#     search_result = f"Search results for: {user_message} - Found relevant information about the topic."
#     return {"search_result": search_result}

# # Node 3: Calculate if needed
# def calculate_node(state: State) -> State:
#     """Handle mathematical calculations"""
#     user_message = state["messages"][-1].content
    
#     calc_prompt = f"""
#     Extract and calculate any mathematical expression from: {user_message}
#     If no math found, respond with "No calculation needed"
#     """
    
#     response = model.invoke([{"role": "user", "content": calc_prompt}])
#     return {"search_result": response.content}

# # Node 4: Generate final response
# def generate_response(state: State) -> State:
#     """Generate the final response using all available information"""
#     user_message = state["messages"][-1].content
#     analysis = state.get("analysis_result", "")
#     search_result = state.get("search_result", "")
    
#     final_prompt = f"""
#     User asked: {user_message}
#     Analysis: {analysis}
#     Additional info: {search_result}
    
#     Provide a helpful, comprehensive response.
#     """
    
#     response = model.invoke([{"role": "user", "content": final_prompt}])
#     return {"messages": [response]}

# # Conditional routing function
# def route_after_analysis(state: State) -> str:
#     """Route to different nodes based on analysis"""
#     analysis = state.get("analysis_result", "").upper()
    
#     if "SEARCH" in analysis:
#         return "search"
#     elif "CALCULATE" in analysis:
#         return "calculate" 
#     else:
#         return "generate_response"

# # Build the custom graph
# graph_builder = StateGraph(State)

# # Add all nodes
# graph_builder.add_node("analyze", analyze_input)
# graph_builder.add_node("search", search_node)
# graph_builder.add_node("calculate", calculate_node)
# graph_builder.add_node("generate_response", generate_response)

# # Add edges
# graph_builder.add_edge(START, "analyze")

# # Conditional routing after analysis
# graph_builder.add_conditional_edges(
#     "analyze",
#     route_after_analysis,
#     {
#         "search": "search",
#         "calculate": "calculate",
#         "generate_response": "generate_response"
#     }
# )

# # Both search and calculate lead to final response
# graph_builder.add_edge("search", "generate_response")
# graph_builder.add_edge("calculate", "generate_response")
# graph_builder.add_edge("generate_response", END)

# # Compile with checkpointer
# agent = graph_builder.compile(checkpointer=checkpoint_saver)

# def display_graph():
#     try:
#         img = agent.get_graph().draw_mermaid_png()
#         with open("custom_graph.png", "wb") as f:
#             f.write(img)
#         print("Graph saved as custom_graph.png")
#     except Exception as e:
#         print(f"Could not display graph: {e}")

# display_graph()

# # Test the custom multi-node agent
# config = {"configurable": {"thread_id": "custom_1"}}

# test_cases = [
#     "What is 25 * 4 + 10?",
#     "Tell me about Python programming",
#     "How are you today?"
# ]

# for test in test_cases:
#     print(f"\n🔹 User: {test}")
#     response = agent.invoke(
#         {"messages": [{"role": "user", "content": test}]}, 
#         config=config
#     )
#     print(f"🤖 Assistant: {response['messages'][-1].content}")
#     print("-" * 50)