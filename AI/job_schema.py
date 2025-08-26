from pydantic import BaseModel ,Field
from typing import List

class JobDescription(BaseModel):
    job_title: str = Field(...,description="The job title, (eg,. Software developer)")
    location: str = Field(...,description="The loacation of the job, (eg,. Bangalore,India)")
    job_type: str = Field(...,description="The job_type, (eg., permenant,contract)") 
    work_mode: str = Field(...,description="The work_mode, (eg., Remote, Hybrid, On-site)") 
    experience_required: str = Field(...,description="The experience for the job, (eg., 2-years experience in python development)") 
    skills: List[str] = Field(...,description="The list of skills, (eg., [python, java, C++])") 
    job_summary: str = Field(...,description="The short summary of job based on the user provided details, (eg.,We are looking for a skilled Python Developer to join our team. The ideal candidate will have a strong background in Python development )") 
    responsibilities: List[str] = Field(...,description="The list of responsibilities, (eg., [Develop and maintain Python-based applications.,  Collaborate with cross-functional teams to define, design, and ship new features.',  Write clean, maintainable, and efficient code])") 


class matching(BaseModel):
    id: str = Field(..., description="The job id must extract from the job description")
    candidate_name : str = Field(...,description="The candidate name must extract from the candidate resume")
    candidate_email:  str = Field(...,description="The candidate email must extract from the candidate resume")
    job_title: str = Field(...,description="The job title must extract from the job description")
    matched: str = Field(...,ge=0 ,le= 100,description="Analyse both resume and candidate resume, and give a matching score from (0-100 %)")
    explanation_for_score: str = Field(...,description="Explain why the matching score is (from 0-100 %), based on the candidate resume")
    explanation_not_for_score: str = Field(...,description="Explain why the matching score is not (100 %) ,based on the candidate resume")