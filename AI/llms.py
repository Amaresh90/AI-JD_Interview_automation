from langchain_google_genai import ChatGoogleGenerativeAI
from AI.env import ENVS_KEYS

# LLM Setup
gemini_llm = ChatGoogleGenerativeAI(
    google_api_key=ENVS_KEYS.get("GOOGLE_API_KEY"),
    model=ENVS_KEYS.get("MODEL"),
)



