from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from dotenv import load_dotenv , find_dotenv
from cryptography.fernet import Fernet
import os

load_dotenv(find_dotenv())

secret_key = os.getenv("SECRET_KEY")
algorithm = os.getenv("ALGORITHM")
fetnet_key = Fernet(os.getenv("FERNET_KEY"))

#OAuth2PasswordBearer to handle token extraction from the request header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

#password hashing context (using bcrypt)
pwd_context = CryptContext(schemes=['bcrypt'] , deprecated = "auto")


#utility function to create JWT access token 
def create_access_token(data: dict, expire_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expire_delta:
        expire = datetime.utcnow() + expire_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp" : expire})
    encode_jwt = jwt.encode(to_encode, secret_key , algorithm)
    return encode_jwt

def create_reset_token(data: dict, expire_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expire_delta:
        expire = datetime.utcnow() + expire_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=10)
    to_encode.update({"exp" : expire})
    encode_jwt = jwt.encode(to_encode, secret_key , algorithm)
    return encode_jwt

#utility function to decode JWT access token
def decode_access_token(token:str):
    try:
        payload = jwt.decode(token, secret_key , algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is invalid")
    
#utility function to verify user password
def verify_password(plain_password: str , hashed_password: str):
    return pwd_context.verify(plain_password , hashed_password)


#utility function to hash user password
def hash_password(password: str):
    return pwd_context.hash(password)


def encrypt_api_key(api_key: str):
    return fetnet_key.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_api_key: str):
    return fetnet_key.decrypt(encrypted_api_key.encode()).decode()

