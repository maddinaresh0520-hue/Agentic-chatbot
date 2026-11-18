from langgraph.graph import StateGraph, START,END,add_messages
from dotenv import load_dotenv
from typing import TypedDict , Annotated,Optional
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage,BaseMessage,AIMessage
from pydantic import BaseModel,Field
from langchain_core.tools import tool 
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

from langgraph.prebuilt import ToolNode, tools_condition
from pathlib import Path
import requests
import sqlite3
import time


load_dotenv(Path(__file__).resolve().with_name("key.env"))


# Tools
search_wrapper = DuckDuckGoSearchAPIWrapper(
    region="us-en",
    backend="html",)
search_tool = DuckDuckGoSearchRun(region="us-en", backend="html", api_wrapper=search_wrapper)

@tool
def search_web(query: str) -> str:
    """Search the web with DuckDuckGo."""
    for attempt in range(2):
        try:
            return search_tool.invoke(query)
        except Exception as e:
            if attempt == 1:
                return f"Search failed after two attempts: {type(e).__name__}: {e}"
            time.sleep(1)


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=NEVZS9DI2VZCFOJD"
    r = requests.get(url)
    return r.json()

tools = [search_web,get_stock_price]
              

model = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")

llm_with_tools = model.bind_tools(tools)


class messages(TypedDict):
     messages : Annotated[list[BaseMessage], add_messages]




def chat_node(state: messages):
    """LLM node that may answer or request a tool call."""
    messages = state['messages']
    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}

tool_node = ToolNode(tools)




conn = sqlite3.connect(database="chatbot_db",check_same_thread=False)

checkpointers = SqliteSaver(conn=conn)



graph = StateGraph(messages)
graph.add_node('chat_node',chat_node)
graph.add_node("tools", tool_node)


graph.add_edge(START,'chat_node')

graph.add_conditional_edges("chat_node",tools_condition)
graph.add_edge('tools', 'chat_node')


chatbot = graph.compile(checkpointer=checkpointers)




def retrive_all_thread_id():
    all_tread_id = set()
    for checkpointer in (checkpointers.list(None)):
        all_tread_id.add(checkpointer.config['configurable']['thread_id'])

    return list(all_tread_id)


