from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from API.domain.domain import domain_router
from API.jd.jds import job_router
from API.users_data.user import hr_router
from API.roles.roles import role_router
from API.login_page.login import login_router
from API.dashboard.dashboard import dashboard_router
from API.upload_resume.resume import resume_router
from API.match_resume.match import match_router


app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	errors = exc.errors()
	details = []
	for err in errors:
		field = err['loc'][-1]
		error_type = err.get('type', 'value_error')
		if error_type == 'value_error.missing':
			details.append({
				"field": field,
				"message": f"{field} Field required",
				"type": "missing"
			})
		# validation for hr_main
		elif field == 'phone_no' and error_type == 'string_pattern_mismatch':
			details.append({
				"field": field,
				"message": "Phone number should contain 10 digits. Examples: 91XXXXXXXXXX / 0XXXXXXXXXX / XXXXXXXXXX",
				"type": "string_pattern_mismatch"
			})
		elif field == 'emp_id' and error_type == 'string_pattern_mismatch':
			details.append({
				"field": field,
				"message": "Employee id should contain 'DB' prefix followed by digits",
				"type": "string_pattern_mismatch"
			})
		elif field == 'email_id' and error_type == 'string_pattern_mismatch':
			details.append({
				"field": field,
				"message": "Email should be in the format 'example@gmail.com'",
				"type": "string_pattern_mismatch"
			})
		# validation for roles.py
		elif field == 'role' and error_type == 'string_pattern_mismatch':
			details.append({
				"field": field,
				"message": "enter the valid role (eg,'HR','Manager'), Avoid using (Manager1,Manager2)",
				"type": "string_pattern_mismatch"
			})
        # validation for domain.py
		elif field == 'domain' and error_type == 'string_pattern_mismatch':
			details.append({
				"field": field,
				"message": "enter valid domain (eg:'@abc.com'),the domain must start with '@'",
				"type": "string_pattern_mismatch"
            })
		elif field == 'password' and error_type == 'string_pattern_mismatch':
			details.append({
				"field": field,
				"message": "Password must contain 1 uppercase, 1 lowercase, 1 digit, and 1 special character",
				"type": "string_pattern_mismatch"
            })
		else:
			details.append({
				"field": field,
				"message": err.get('msg', 'Invalid value'),
				"type": error_type
			})
	return JSONResponse(
		status_code=422,
		content={
			"status_code": 422,
			"error": "Validation Error",
			"details": details
		}
	)

# Include the domain router
app.include_router(domain_router, prefix="/domains", tags=["Domains"])
app.include_router(job_router, prefix="/jds", tags=["Job Descriptions"])
app.include_router(hr_router, prefix="/user", tags=["user details"])
app.include_router(role_router, prefix="/role", tags=["role details"])
app.include_router(login_router, prefix="/login_page", tags=["login page details"])
app.include_router(dashboard_router,prefix="/dashboard", tags=["Dashboard"])
app.include_router(resume_router,prefix="/resume", tags=["upload resume"])
app.include_router(match_router,prefix="/match", tags=["match"])