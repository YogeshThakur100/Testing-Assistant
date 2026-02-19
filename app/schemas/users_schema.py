from pydantic import BaseModel , EmailStr, Field


class addUserBase(BaseModel):
    email : EmailStr = Field(description= "User's email address")
    password : str = Field(description= "User's password")
    conformPassword : str = Field(description= "User's conform password")


class loginBase(BaseModel):
    email : EmailStr = Field(description= "User's email address")
    password : str = Field(description= "User's password")


class addApiKeyBase(BaseModel):
    api_key : str = Field(description= "User's API key")

class resetPasswordBase(BaseModel):
    email : str

class resetPasswordConfromBase(BaseModel):
    password : str = Field(description= "User's password")
    conformPassword : str = Field(description= "User's conform password")