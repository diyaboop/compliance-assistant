from langgraph.graph import StateGraph, END
from agents import ComplianceState, research_agent, analysis_agent, writing_agent

def build_pipeline():
    # create graph
    graph = StateGraph(ComplianceState)

    # add three nodes
    graph.add_node("research", research_agent)
    graph.add_node("analysis", analysis_agent)
    graph.add_node("writing",writing_agent)

    # set entry point
    graph.set_entry_point("research")

    # add edges
    graph.add_edge("research", "analysis")
    graph.add_edge("analysis","writing")
    graph.add_edge("writing", END)

    # compile and return
    return graph.compile()
    
