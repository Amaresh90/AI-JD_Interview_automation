# ------------------- JD page--------------------
def jd_details(jd):
    return {
        "id": str(jd["_id"]),
        "job_title": jd.get("job_title"),
        "description": jd.get("description"),
        "requirements": jd.get("requirements"),
        "location": jd.get("location"),
        "is_active": jd.get("is_active", True)
    }

def all_jd_details(jds):
    return [jd_details(jd) for jd in jds]




# ------------------hr page-----------------------
def hr_details(hr):
    return{
        "id": str(hr["_id"]),
        "full_name": hr.get("full_name"),
        "emp_id": hr.get("emp_id"),
        "phone_no": hr.get("phone_no"),
        "email_id": hr.get("email_id"),
        "password": hr.get("password"),
        "role": hr.get("role"),
        "is_active":hr.get("is_active"),
    }

# return in list
def all_details(hrs):
    return [hr_details(hr) for hr in hrs]


# ------------------- domain page--------------------
def domain_details(domain):
    return {
        "id": str(domain["_id"]),
        "domain": domain["domain"],
        "is_active":domain["is_active"]
    }

def all_domain_details(domains):
    return [domain_details(domain) for domain in domains]

# # ------------------- Role page--------------------
def role_details(role):
    return {
        "id": str(role["_id"]),
        "role": role["role"],
        "is_active":role["is_active"]
    }

def all_role_details(roles):
    return [role_details(role) for role in roles]