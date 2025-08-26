from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal
from AI.backend_main import job_description_chain
from AI.prompt import modification_prompt, output_parser
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver
import json
from AI.db import get_mongo_collection
from datetime import datetime

load_dotenv()

llm = ChatGoogleGenerativeAI(
    google_api_key=os.environ["GOOGLE_API_KEY"],
    model="gemini-2.0-flash"
).with_config(response_mime_type="text/plain")

modification_chain = modification_prompt | llm | StrOutputParser()

config = {"configurable": {"thread_id": "123"}}

class JDstate(TypedDict):
    user_input: dict
    session_id: str
    generated_jd: str
    modified_jd: str
    final_jd: str
    file_status: str
    feedback_choice: Literal["generate", "modification"]
    modification_request: str
    modification_count: int

# NODE 1: generate jd ------------>
def generate_jd_nodes(state: JDstate) -> JDstate:
    # print("generate state:---->",state)
    print("\n entering to generated jd node")
    # print("state:---->",state)
    result = job_description_chain.invoke(
        input=state["user_input"],
        config={"configurable": {"session_id": state["session_id"]}},
    )
    jd = output_parser.invoke(result.content)
    # Ensure jd is a JSON string
    if isinstance(jd, dict):
        jd_json = json.dumps(jd)
    elif isinstance(jd, str):
        try:
            # Try to parse and re-dump to ensure valid JSON string
            jd_json = json.dumps(json.loads(jd))
        except Exception:
            jd_json = json.dumps({"job_description": jd})
    else:
        jd_json = json.dumps({"job_description": str(jd)})
    return {**state, "generated_jd": jd_json}
print("\n exiting from generated jd node")

# NODE 2: feedback ------------>
def feedback_nodes(state: JDstate) -> JDstate:
    print("\n Entering feedback_nodes")
    choice = interrupt("Do you want to proceed with the generated JD or request modification? (generate/modification):")
    print("\n Exiting feedback_nodes")
    return {"feedback_choice": choice}

# NODE 3: gmodification ------------>
def modification_nodes(state: dict) -> JDstate:
    print("\n ----sEntering modification_node")
    # print("\n state:--->", state)
    mod_request = state.get("modification_request")
    if not mod_request:
        # Try to get from feedback_choice if it's a dict
        feedback = state.get("feedback_choice", {})
        if isinstance(feedback, dict):
            mod_request = feedback.get("modification_request", "")
    print("\n------>mod_request---->", mod_request)
    jd = state.get("generated_jd", "")

    # print("User requested modification:", mod_request)
    print("Original JD:", jd)

    messages = modification_prompt.invoke(input={
        "original_jd": jd,
        "modification_request": mod_request
    })
    # print("Prepared messages:", messages)

    # Invoke the LLM
    response = llm.invoke(messages)

    final_jd = response.content.strip() if hasattr(response, 'content') else str(response)
    print("Final Modified JD:", final_jd)

    try:
        final_jd_json = json.dumps(json.loads(final_jd))
    except Exception:
        final_jd_json = json.dumps({"job_description": final_jd})
    print("\n final_jd_json:--->", final_jd_json)

    print("---- Exiting modification_node\n")
    return {
        **state,
        "modified_jd": final_jd_json,
        "generated_jd": state.get("generated_jd", "")
    }

# NODE 4: final generate jd ------------>
def final_generate_jd_node(state: JDstate) -> JDstate:
    print("\n entering to final_generate_jd_node")
    print("\n final jd state:-->", state)

    final_jd_raw = state.get("modified_jd")

    if final_jd_raw and isinstance(final_jd_raw, str) and final_jd_raw.strip():
        try:
            # Convert JSON string to dict
            parsed_final_jd = json.loads(final_jd_raw)
            state["final_jd"] = parsed_final_jd
        except Exception as e:
            print(" Failed to parse modified_jd:", e)
            # Fallback to generated_jd
            try:
                state["final_jd"] = json.loads(state.get("generated_jd", "{}"))
            except:
                state["final_jd"] = state.get("generated_jd", "")
    else:
        try:
            state["final_jd"] = json.loads(state.get("generated_jd", "{}"))
        except:
            state["final_jd"] = state.get("generated_jd", "")

    print("\n exiting from final_generate_jd_node")
    return state

# NODE : decition after feedback ------------>
def decide_after_feedback(state: JDstate) -> str:
    print("\n -- entering to decide_after_feedback node ---")
    if state["feedback_choice"] == "generate":
        next_node = "final_generate_jd_node"
    else:
        next_node = "modification_nodes"
    # print("Routing to:", next_node)
    print("\n -- exiting from decide_after_feedback node ---")
    return next_node

# NODE 5: save final generate jd ------------>
def save_node(state: JDstate) -> JDstate:
    
    print("\n -- entering to save node---")
    # print("\n state:-->",state)
    final_jd = state.get("final_jd")
    if final_jd is None:
        raise ValueError("State must contain 'final_jd' field.")

    if isinstance(final_jd, str):
        try:
            final_jd_obj = json.loads(final_jd)
        except Exception:
            final_jd_obj = {"job_description": final_jd}
    elif isinstance(final_jd, dict):
        final_jd_obj = final_jd
    else:
        raise ValueError("'final_jd' must be a str or dict.")

    doc = {
    **final_jd_obj,
    "is_draft": True,
    "is_published": False,
    "published_at": None,
    "created_at": datetime.now().isoformat()  
}
     
    collection = get_mongo_collection()
    result = collection.insert_one(doc)
    print(f"Saved JD to MongoDB with _id: {result.inserted_id}")
    print("\n -- exiting from save node---")
    return {**state, "mongo_id": str(result.inserted_id)}

# NODE 6: restar_node ------------>

def restart_node(state: JDstate) -> JDstate:
    print("\n -- entering to restart node---")
    # print("state:---->", state)
    reset_state = {
        "user_input": {},
        "session_id": "",
        "generated_jd": None,
        "modified_jd": "",
        "final_jd": None,
        "file_status": None,
        "feedback_choice": None,
        "file_format": ".txt",
        "modification_request": None,
        "modification_count": 0
    }
    print("\n -- exiting from restart node---")
    return reset_state

# CREATE GRAPH: generate jd ------------>
def create_jd_graph():
    builder = StateGraph(JDstate)
    checkpointer = InMemorySaver()

    builder.add_node("generate_jd_nodes", generate_jd_nodes)
    builder.add_node("feedback_nodes", feedback_nodes)
    builder.add_node("modification_nodes", modification_nodes)
    builder.add_node("final_generate_jd_node", final_generate_jd_node)
    builder.add_node("save_node", save_node)
    # builder.add_node("restart_node", restart_node)

    builder.set_entry_point("generate_jd_nodes")
    builder.add_edge("generate_jd_nodes", "feedback_nodes")

    builder.add_conditional_edges("feedback_nodes", decide_after_feedback, {
        "modification_nodes": "modification_nodes",
        "final_generate_jd_node": "final_generate_jd_node",
    })
    builder.add_edge("modification_nodes", "final_generate_jd_node")
    builder.add_edge("final_generate_jd_node", "save_node")
    builder.add_edge("save_node", END)
    # builder.add_edge("save_node", "restart_node")
    # builder.add_edge("restart_node", END)

    graph = builder.compile(checkpointer=checkpointer)
    with open("g.png", "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())
    return graph

graph = create_jd_graph()
