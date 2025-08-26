# ------------------hr page-----------------------
def hr_details(hr):
    return{
        "full_name": hr.get("full_name"),
        "emp_id": hr.get("emp_id"),
        "phone_no": hr.get("phone_no"),
        "email_id": hr.get("email_id"),
        "password": hr.get("password"),
        "role": hr.get("role"),
    }

# return in list
def all_details(hrs):
    return [hr_details(hr) for hr in hrs]


# ------------------- domain page--------------------
def domain_details(domain):
    return {
        "id": str(domain["_id"]),
        "domain": domain["domain"],
    }

def all_domain_details(domains):
    return [domain_details(domain) for domain in domains]

# # ------------------- Role page--------------------
def role_details(role):
    return {
        "id": str(role["_id"]),
        "role": role["role"],
    }

def all_role_details(roles):
    return [role_details(role) for role in roles]

# ----jds
def jd_details(jd):
    return{
        "job_title": jd.get("job_title"),
        "location": jd.get("location"),
        "job_type": jd.get("job_type"),
        "work_mode": jd.get("work_mode"),
        "experience_required": jd.get("experience_required"),
        "skills": list[str(jd.get("skills"))]
       
    }

# return in list
def all_jd_details(jds):
    return [jd_details(jd) for jd in jds]
