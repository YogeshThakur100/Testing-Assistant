from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from models import users_model
from database.session import get_db
import JWTutils
import csv
import io 


Oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/users/login')


def verify_token(token: str = Depends(Oauth2_scheme) , db : Session = Depends(get_db)):
    try:
        payload = JWTutils.decode_access_token(token)
        email = payload.get("email")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: email not found"
            )
        
        user = db.query(users_model.User).filter(users_model.User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return {"email": user.email , "user_id" : user.id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
    

def vertify_reset_password_token(token: str = Depends(Oauth2_scheme) , db : Session = Depends(get_db)):
    try:
        payload = JWTutils.decode_access_token(token)
        token_type = payload.get('type')
        email = payload.get('email')

        if token_type != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token: not a password reset token"
            )
        
        if not email:
            raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: email not found"
                )
        

        user = db.query(users_model.User).filter(users_model.User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )


        return {"email" : user.email}   

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

def format_bdd(bdd: str) -> str:
    return f"""```gherkin
{bdd or ""}
```"""


def convert_json_to_csv(data: list) -> str:
    if not data:
        return ""

    output = io.StringIO()
    
    # Use keys from first row as headers
    headers = data[0].keys()
    
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(data)

    return output.getvalue()