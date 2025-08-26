from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pathlib import Path
from PyPDF2 import PdfReader
import json
from AI.prompt import matching_prompt, output_parser_match 
from langchain_core.output_parsers import StrOutputParser
from langgraph.types import interrupt
import uuid
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver
from AI.env import ENVS_KEYS 
from AI.llms import gemini_llm 
from langchain_core.prompts import ChatPromptTemplate
from AI.qa_prompt import display_code_prompt, display_theory_prompt 
import json
from database.config import jd_collection

# === STATE ===
class MatchState(TypedDict):
    session_id: str
    jd_list: List[str]
    resumes: List[Dict[str, str]]
    current_resume_file: str
    scores: Dict[str, int]
    list_match: List[str]
    total_resume: int
    resume_done: int
    matches: List[Dict] 
    user_decision: str
    generate_qa: List[Dict] 
    input_values: dict

# ===== chain for theory and coding prompt ====
theory_chain = ChatPromptTemplate.from_messages(display_theory_prompt) | gemini_llm
coding_chain = ChatPromptTemplate.from_messages(display_code_prompt) | gemini_llm

# === NODE 1: Database ===
def database_node(state: MatchState) -> MatchState:
    print("\n enter to database node-----")

    results = jd_collection.find(
        {"is_active": True},
        projection={
            "_id": 1,
            "job_title": 1,
            "location": 1,
            "job_type": 1,
            "work_mode": 1,
            "experience_required": 1,
            "skills": 1,
            "job_summary": 1,
            "responsibilities": 1
        }
    )
    formatted_results = []
    for doc in results:
        doc["_id"] = str(doc["_id"])
        if isinstance(doc.get("skills"), dict):
            doc["skills"] = list(doc["skills"].values())
        if isinstance(doc.get("responsibilities"), dict):
            doc["responsibilities"] = list(doc["responsibilities"].values())
        formatted_results.append(doc)

    state["jd_list"] = json.dumps(formatted_results, indent=2)
    print("\nFormatted JD List:")
    print(state["jd_list"])
    print("\n exit from database node-----")
    return state

# === NODE2: Resume Reader ===
def resume_node(state: MatchState) -> MatchState:
    print("\n enter to resume node-----")
    if state.get("resumes"):
        print("Resumes already loaded. Skipping.")
        return state

    folder = Path(ENVS_KEYS.get("RESUME_FOLDER"))
    resumes = list(folder.glob("*.pdf"))

    if not resumes:
        raise ValueError("No resumes found in the folder!")

    extracted_resumes = []
    for resume_path in resumes:
        try:
            reader = PdfReader(resume_path)
            resume_text = ''.join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            print(f"Error reading {resume_path.name}: {e}")
            resume_text = ""

        extracted_resumes.append({
            "file_name": resume_path.name,
            "text": resume_text
        })

    state["resumes"] = extracted_resumes
    state["total_resume"] = len(extracted_resumes)
    state["resume_done"] = 0
    print("exit from resume node-----")
    return state

# === NODE 3: Matching ===
def matching_node(state: MatchState) -> MatchState:
    print("\n enter to matching node-----")
    matches = state.get("matches", [])
    resumes = state.get("resumes", [])
    jd_list = json.loads(state.get("jd_list", "[]"))
    resume_done_count = state.get("resume_done", 0)

    print("\n resumes--->", resume_done_count)
    print("\n resumes", resumes)

    if resume_done_count < len(resumes):
        resume = resumes[resume_done_count]
    else:
        print(f" Index {resume_done_count} is out of range for resumes list of length {len(resumes)}")
        return state

    resume_text = resume.get("text", "")
    resume_file = resume.get("file_name", "Unknown")
    print(f"Processing resume: @{resume_file}")

    batch_list = []
    for jd in jd_list:
        jd_text = "\n".join([
            f"id: {jd.get('_id', '')}",
            f"Title: {jd.get('job_title', '')}",
            f"Location: {jd.get('location', '')}",
            f"Type: {jd.get('job_type', '')}",
            f"Mode: {jd.get('work_mode', '')}",
            f"Experience: {jd.get('experience_required', '')}",
            f"Skills: {', '.join(jd.get('skills', [])) if isinstance(jd.get('skills'), list) else jd.get('skills', '')}",
            f"Summary: {jd.get('job_summary', '')}"
        ])
        batch_list.append({"jd_text": jd_text, "resume_text": resume_text})

    chain = matching_prompt | gemini_llm | StrOutputParser()
    responses = chain.batch(batch_list)

    for i, resp in enumerate(responses):
        print("\n LLM response ---->", resp)
        try:
            parsed = output_parser_match.parse(resp)
            matches.append(parsed)
        except Exception as e:
            print(f"Error parsing response {i}: {e}")

    state["matches"] = matches
    state["resume_done"] = resume_done_count + 1
    print("exit from matching node-----")
    return state

# === NODE 4: HUMAN NODE ===
def human_node(state: MatchState):
    print("enter to human node----")
    user_input = interrupt("Do you want to go to the next resume? (yes/no): ")
    if user_input == "yes" and state.get("resume_done") < state.get("total_resume"):
        return Command(goto="matching_node", update=state)
    else:
        print("\n end \n")
        return Command(goto=END, update=state)

# === NODE 5 : GENERATE QA ===
def generate_qa_node(state: MatchState) -> MatchState:
    print("\n=== Entering generate_qa_node ===")

    input_values = state["input_values"]
    selected_type = input_values.get("question", "theory").strip().lower()

    jds_to_process = state.get("matches", []) 
    generated_qa_list = []

    try:
        required_keys = ["level", "range_values", "type_question", "job_title"]
        if not all(k in input_values for k in required_keys):
            raise ValueError(f"Missing input fields: {', '.join(k for k in required_keys if k not in input_values)}")

        # Iterate only through the JD matches provided for QA generation
        if not jds_to_process:
            raise ValueError("No JDs provided for QA generation.")

        for jd_info in jds_to_process:
            job_title = jd_info.get("job_title", "Unknown Role")
            job_id = jd_info.get("id", "Unknown ID")
            print(f"\nGenerating Q&A for JD: {job_title} (ID: {job_id})")

            resume_index = state.get("resume_done", 0) - 1
            if resume_index >= 0 and resume_index < len(state.get("resumes", [])):
                current_resume_text = state["resumes"][resume_index].get("text", "")
            else:
                current_resume_text = ""
                print(f"Warning: Could not find resume text for index {resume_index}. QA might be less accurate.")


            qa_input = input_values.copy()
            qa_input["job_title"] = job_title
            qa_input["resume_text"] = current_resume_text 

            qa_input["job_skills"] = ', '.join(jd_info.get("skills", [])) if isinstance(jd_info.get("skills"), list) else jd_info.get("skills", "N/A")
            qa_input["job_responsibilities"] = '\n'.join(jd_info.get("responsibilities", [])) if isinstance(jd_info.get("responsibilities"), list) else jd_info.get("responsibilities", "N/A")
            qa_input["job_summary"] = jd_info.get("job_summary", "N/A")


            if selected_type == "theory":
                result = theory_chain.invoke(qa_input)
            elif selected_type == "coding":
                result = coding_chain.invoke(qa_input)
            else:
                raise ValueError("Invalid question type: must be 'theory' or 'coding'.")

            print(f"Raw LLM output for {job_title}:\n{result.content}\n")
            try:
                # Try to parse as JSON first
                parsed_output = json.loads(result.content)
                if not isinstance(parsed_output, list):
                    parsed_output = [{"raw_output": result.content}]
            except json.JSONDecodeError:
                print(f"JSONDecodeError: Could not parse LLM output for {job_title}. Attempting fallback parsing.")
                # Fallback: parse plain text Q&A pairs
                qa_pairs = []
                lines = result.content.split('\n')
                question = None
                answer = None
                for line in lines:
                    line = line.strip()
                    if line.lower().startswith('question'):
                        if question and answer:
                            qa_pairs.append({"question": question, "answer": answer})
                        # Remove 'Question X:' prefix
                        colon_index = line.find(':')
                        if colon_index != -1:
                            question = line[colon_index+1:].strip()
                        else:
                            question = line
                        answer = None
                    elif line.lower().startswith('answer:'):
                        answer = line[len('Answer:'):].strip()
                    elif answer is not None:
                        # Append additional answer lines
                        answer += '\n' + line
                if question and answer:
                    qa_pairs.append({"question": question, "answer": answer})
                parsed_output = qa_pairs if qa_pairs else [{"raw_output": result.content}]

            generated_qa_list.append({
                "job_title": job_title,
                "job_id": job_id,
                "qa": parsed_output
            })

        print("\n=== All QAs for this resume ===")
        print(json.dumps(generated_qa_list, indent=2))

    except Exception as e:
        print(f"Error in generate_qa_node: {e}")
        generated_qa_list.append({"error": str(e)})

    print("=== Exiting generate_qa_node ===\n")
    return {
        **state,
        "generate_qa": generated_qa_list,
        "user_decision": "done" 
    }

# === GRAPH ===
def match_graph():
    builder = StateGraph(MatchState)
    checkpointer = InMemorySaver()

    builder.add_node("database_node", database_node)
    builder.add_node("resume_node", resume_node)
    builder.add_node("matching_node", matching_node)
    builder.add_node("human_node", human_node)
    builder.add_node("generate_qa_node", generate_qa_node)

    builder.set_entry_point("database_node")
    builder.add_edge("database_node", "resume_node")
    builder.add_edge("resume_node", "matching_node")
    builder.add_edge("matching_node", "human_node") 
    builder.add_edge("human_node", END) 

    graph = builder.compile(checkpointer=checkpointer)

    with open("match1.png", "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())

    return graph

match_graph()

# === RUN ===
if __name__ == "__main__":
    session_id = str(uuid.uuid4())
    graph = match_graph()

    state: MatchState = {
        "session_id": session_id,
        "jd_list": "",
        "resumes": [],
        "current_resume_file": "",
        "scores": {},
        "list_match": [],
        "total_resume": 0,
        "resume_done": 0,
        "matches": [],
        "user_decision": "",
        "generate_qa": [],
        "input_values": {
            "question": "theory",
            "level": "beginner",
            "range_values": 1, 
            "type_question": "theory"
        }
    }

