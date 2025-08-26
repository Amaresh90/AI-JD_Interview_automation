from pydantic import BaseModel,Field,EmailStr

class hr(BaseModel):
    full_name: str = Field(..., description="Full name of the HR")
    emp_id: str = Field(..., pattern=r'^DB\d+$', description="Must start with DB followed by digits")
    phone_no: str = Field(..., pattern=r"^(91\d{10}|0\d{10}|\d{10})$", description="Phone number with optional 91 or 0 prefix")
    email_id: EmailStr = Field(..., description="Valid email is required")
    password: str =Field(..., min_length=8, description="Password must contain 1 uppercase, 1 lowercase, 1 digit, and 1 special character")
    role: str

class domain(BaseModel):
    domain: str = Field(..., description=" The domain id should be valid format")