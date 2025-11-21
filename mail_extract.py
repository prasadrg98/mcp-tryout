from dotenv import load_dotenv
load_dotenv()

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel

checkpoint_saver = InMemorySaver()

class MailResponse(BaseModel):
    subject: str
    body: str

agent = create_react_agent(
    model="groq:llama-3.3-70b-versatile",
    tools=[],
    response_format=MailResponse,
    checkpointer=checkpoint_saver
)

# class MailResponse(BaseModel):
#    subject: str
#    body: str


# agent = create_react_agent(
#    model="groq:llama-3.3-70b-versatile", 
#    tools=[], 
#    response_format = MailResponse 
# )


config = {"configurable": {"thread_id": "1"}}
response = agent.invoke(
    {"messages": [{"role": "user", "content": "write a mail applying leave for travel"}]}, config=config
)

print(response["structured_response"])
print("*" * 40)
print(response["structured_response"].subject)
print("*" * 40)
print(response["structured_response"].body)
