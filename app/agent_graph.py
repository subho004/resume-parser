from app.webagent import web_agent
from langgraph.graph import StateGraph, START, END
from typing import Iterable, List, TypedDict

class State(TypedDict):
    content: str
    analysis: str

def analyse_node(state: State) -> State:
    # Placeholder for analysis logic
    analysis_result = web_agent(state["content"])
    state["analysis"] = analysis_result
    return state

def build_graph():
    graph = StateGraph(State)
    graph.add_node("analyse", analyse_node)
    graph.set_entry_point("analyse")
    graph.set_finish_point("analyse")
    return graph.compile()