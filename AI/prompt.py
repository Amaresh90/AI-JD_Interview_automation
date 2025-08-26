# from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate,ChatPromptTemplate
# from langchain.output_parsers import PydanticOutputParser
# from langchain.output_parsers.json import SimpleJsonOutputParser
# from AI.job_schema import JobDescription
# # from match_schema import matching

# parser = SimpleJsonOutputParser(pydantic_object=JobDescription)
# # parser_match = SimpleJsonOutputParser(pydantic_object=matching)

# display_prompt = [
#     SystemMessagePromptTemplate.from_template(
#         """
# You are an AI-powered HR Assistant.

# Your task is to generate a  well-structured job description in **valid JSON format** using the user-provided information.

# **Instructions:**
# - use the user-provided information, which includes input fields keys: **job_type,loacation,job_type,work_mode,experiene_required,skills**
# - while generating the Job description ,don't skip any information which is provided by the user.
# - analyse the provided input fields to generate:
#   - A **job_summary** (1-2 lines).
#   - A list of **responsibilities** should be in (5-6  points), just use **bullet points**.
#   - Don't display the responsibilitties with both bullet points and numarical. 
# - The final output must be in JSON format.
# - If any field is missing or left blank, instruct the user to provide a value or type "NA" if not applicable.
# - Do **NOT** include any Markdown formatting.
# - Do **NOT** include any explanation or extra text — only return valid JSON.
# """
#     ),
#     HumanMessagePromptTemplate.from_template(
#         """
# Here are the user's inputs:

# - job_title: {job_title}
# - location: {loc}
# - job_type: {job_type}
# - work_mode: {work_mode}
# - experience Required: {exp}
# - skills: {skills}

# - Based on this input, please generate the **job_summary** and **responsibilities**.

# """
#     )
# ]


# output_parser = parser


# modification_prompt = ChatPromptTemplate.from_messages([
#     (
#         "system",
#         """You are an expert job description assistant.
# You will be given a job description in JSON format and a **modification_request** to modify it.
# Take the **modification_request**, analyse it, and return ONLY the complete modified job description as a final JD JSON object.

# Important:
# - For the "skills" and "responsibilities" fields, return them as JSON objects with numeric string keys ("0", "1", ...) instead of arrays.
# - Do NOT wrap the output in triple backticks or any code block formatting.
# - Do NOT add a top-level "job_description" key unless explicitly requested.
# - You will be given a job description in JSON format and a modification request.
# - Modify the JSON as per the request and return ONLY the full modified job description as a strict JSON object.
# - Only update based on the **modification_request**.
# - Do not skip to analyse and extract the **modification_request**.
# - Do not include any explanations or markdown.
# - Ensure all keys and strings use double quotes (") as required by strict JSON format.
# """,
#     ),
#     (
#         "human",
#         "Original JD JSON:\n{original_jd}\n\nUser Modification Request:\n{modification_request}",
#     ),
# ])


from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate,ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.output_parsers.json import SimpleJsonOutputParser
from AI.job_schema import JobDescription,matching
# from match_schema import matching

parser = SimpleJsonOutputParser(pydantic_object=JobDescription)
parser_match = SimpleJsonOutputParser(pydantic_object=matching)

display_prompt = [
    SystemMessagePromptTemplate.from_template(
        """
You are an AI-powered HR Assistant.

Your task is to generate a  well-structured job description in **valid JSON format** using the user-provided information.

**Instructions:**
- use the user-provided information, which includes input fields keys: **job_type,loacation,job_type,work_mode,experiene_required,skills**
- while generating the Job description ,don't skip any information which is provided by the user.
- analyse the provided input fields to generate:
  - A **job_summary** (1-2 lines).
  - A list of **responsibilities** should be in (5-6  points), just use **bullet points**.
  - Don't display the responsibilitties with both bullet points and numarical. 
- The final output must be in JSON format.
- If any field is missing or left blank, instruct the user to provide a value or type "NA" if not applicable.
- Do **NOT** include any Markdown formatting.
- Do **NOT** include any explanation or extra text — only return valid JSON.
"""
    ),
    HumanMessagePromptTemplate.from_template(
        """
Here are the user's inputs:

- job_title: {job_title}
- location: {loc}
- job_type: {job_type}
- work_mode: {work_mode}
- experience Required: {exp}
- skills: {skills}

- Based on this input, please generate the **job_summary** and **responsibilities**.

"""
    )
]


output_parser = parser

modification_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert job description assistant.
You will be given a job description in JSON format and a **modification_request** to modify it.
Take the **modification_request**, analyse it, and return ONLY the complete modified job description as a final JD JSON object.

Important:
- For the "skills" and "responsibilities" fields, return them as JSON objects with numeric string keys ("0", "1", ...) instead of arrays.
- Do NOT wrap the output in triple backticks or any code block formatting.
- Do NOT add a top-level "job_description" key unless explicitly requested.
- You will be given a job description in JSON format and a modification request.
- Modify the JSON as per the request and return ONLY the full modified job description as a strict JSON object.
- Only update based on the **modification_request**.
- Do not skip to analyse and extract the **modification_request**.
- Do not include any explanations or markdown.
- Ensure all keys and strings use double quotes (") as required by strict JSON format.
""",
    ),
    (
        "human",
        "Original JD JSON:\n{original_jd}\n\nUser Modification Request:\n{modification_request}",
    ),
])



matching_prompt = ChatPromptTemplate.from_messages([
    ("""
- You are a job matching assistant. 
- extract the candidate name and candidate email from the resume.
- extract the id and job_title from the job description.     
- Rate how well the resume matches the job description below on a scale of (0-100 %).
- Analyse both the resume and job description, and analyse how much does they match.
- Give a matching score from (0-100 %) (where 100% = perfect match, 0% = not related). Respond with  the number and give explanation.
- Explain why the matched score is (0-100 %). 
- The match score and the explanation should be based on the candidate resume, explain what is there in the resume and why the score has given based on the resume.
- If in the resume there is lack of skills or no skills based on the job description,then give  the score has ( between 0-10 %) , based on the resume and give explanation for it.           
- The explanation should be in (1-2 lines) 
- In **explanation_for_score**, explain only why the candidate has got the score (0-100 %). 
- In **explanation_not_for_score**, explain why the candidate has not got the score 100%. 
- DONT give the same explanation for both **explanation_for_score** and **explanation_not_for_score**
- the output should be in JSON format as following:

Example format:
{{
  "id": "<id>",
  "candidate_name": "<name>",
  "candidate_mail_id": "<email>",
  "job_title": "<job title>",
  "matched": "<score (0-100 %))>",
  "explanation_for_score": "<brief explanation>"
  "explanation_not_for_score": "<brief explanation>"
}}

 
Job Description:
\"\"\"
{jd_text}
\"\"\"

Resume:
\"\"\"
{resume_text}
\"\"\"
"""),
])

output_parser_match = parser_match