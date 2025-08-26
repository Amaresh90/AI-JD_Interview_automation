import os
import re
import json
from uuid import uuid4
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.output_parsers import JsonOutputParser

from AI.prompt import display_prompt, output_parser
from AI.env import ENVS_KEYS


load_dotenv()

def extract_and_print_json(ai_message):
    print()
    if hasattr(ai_message, 'content'):
        content = ai_message.content.strip()
        
        match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        print("\nmatch :---> ", match)
        if not match:
            print("\n Not Match : -->", match)
            match = re.search(r"{.*}", content, re.DOTALL)

        if match:
            json_str = match.group(0)
            print("\n json_str :--> ", json_str)
            try:
                parsed = json.loads(json_str)
                return parsed
            except Exception as e:
                print("JSON parse error:", e)
                return json_str  
        else:
            return content
    return str(ai_message)


def normalize_job_description_output(output):
    return extract_and_print_json(output)  # must return dict


llm = ChatGoogleGenerativeAI(
    google_api_key=os.environ["GOOGLE_API_KEY"],
    model="gemini-2.0-flash"
)

prompt = ChatPromptTemplate.from_messages(display_prompt)
# chain = prompt | llm | output_parser | (lambda obj: AIMessage(content=obj.json(indent=2)))
chain = prompt | llm

store: dict[str, InMemoryChatMessageHistory] = {}

def get_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

job_description_chain = RunnableWithMessageHistory(
    chain,
    get_session_history=get_history,
    input_messages_key="job_title"
)

# result = chain.invoke({"job_title":"Python developer","loc":"mysore","job_type":"permenant","work_mode":"remote","exp":"2 years","skills":"python,java"})
# print(result)
