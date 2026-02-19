from datetime import timedelta
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from database.session import get_db
from main import main_app
from schemas import users_schema 
from models import users_model 
from sqlalchemy.orm import Session
import JWTutils
import dependecies
import emailFunctionality

app = APIRouter()

################helper function###################

def get_user_by_email(email : str , db : Session):
    return db.query(users_model.User).filter(users_model.User.email == email).first()

################helper function###################

@app.post('/add-user')
def add_user(user : users_schema.addUserBase , db : Session = Depends(get_db)):
    try:
        existing_user = db.query(users_model.User).filter(users_model.User.email == user.email).first()
        if existing_user:
            return JSONResponse(
                status_code=409,
                content={
                    "success" : False,
                    "message" : "User already exists"
                }
            )
        
        if user.password != user.conformPassword:
            return JSONResponse(
                status_code=400,
                content={
                    "success" : False,
                    "message" : "Passwords do not match"
                }
        )
        hashed_password = JWTutils.hash_password(user.password)
        new_user = users_model.User(email=user.email, password=hashed_password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return JSONResponse(
            status_code=200,
            content={
                "success" : True,
                "message" : "User created successfully",
                "data": {
                    "email": new_user.email
                }
            }
        )
    except Exception as e:
        print(f"Error creating user: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success" : False,
                "message" : "Internal server error",
                "error": str(e)
            }
        )

@app.post('/login')
def login(user : users_schema.loginBase , db : Session = Depends(get_db)):
    existing_user = db.query(users_model.User).filter(users_model.User.email == user.email).first()

    if not existing_user:
        return JSONResponse(
            status_code=404,
            content={
                "success" : False,
                "message" : "User not found"
            }
        )
    

    if not JWTutils.verify_password(user.password , existing_user.password):
        return JSONResponse(
            status_code=401,
            content={
                "success" : False,
                "message" : "Invalid credentials"
            }
        )
    
    if not existing_user.is_active:
        return JSONResponse(
            status_code=403,
            content={
                "success" : False,
                "message" : "User account is inactive"
            }
        )
    
    token = JWTutils.create_access_token(data={"email": existing_user.email , "user_id" : existing_user.id})
    return JSONResponse(
        status_code=200,
        content={
            "success" : True,
            "message" : "Login successful",
            "token" : token
        }
    )

@app.post('/send-reset-password-link')
def send_reset_password_link(data : users_schema.resetPasswordBase , db : Session = Depends(get_db)):
    existing_user = get_user_by_email(data.email , db)

    if existing_user:
        token = JWTutils.create_reset_token(data=
            {
            "email" : data.email,
            "type" : "password_reset"
            } , 
            expire_delta=timedelta(minutes=10)
        )
        emailFunctionality.EmailUtils.send_reset_password_email(data.email , token , "http://localhost:8080/reset-password")

    return JSONResponse(
        status_code=200,
        content={
            "success" : True,
            "message" : "If the email exists, a reset link has been sent."
        }
    )


@app.post('/reset-password')
def reset_password(user : users_schema.resetPasswordConfromBase, payload : dict = Depends(dependecies.vertify_reset_password_token)  , db : Session = Depends(get_db)):
    try:
        if user.password != user.conformPassword:
            return JSONResponse(
                status_code=400,
                content={
                    "success" : False,
                    "message" : "Passwords do not match"
                }
            )
        
        email = payload.get("email")
        if not email:
            return JSONResponse(
                status_code=400,
                content={
                    "success" : False,
                    "message" : "Invalid token payload"
                }
            )
        
        existing_user = get_user_by_email(email, db)
        if not existing_user:
            return JSONResponse(
                status_code=404,
                content={
                    "success" : False,
                    "message" : "User not found"
                }
            )

        
        hashed_password = JWTutils.hash_password(user.password)
        existing_user.password = hashed_password
        db.commit()
        db.refresh(existing_user)
        return JSONResponse(
            status_code=200,
            content={
                "success" : True,
                "message" : "Password reset successful"
            }
        )
    except Exception as e:
        print(f"Error resetting password: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success" : False,
                "message" : "Internal server error",
                "error": str(e)
            }
        )

@app.post('/add-api-key')
def add_api_key(api_key : users_schema.addApiKeyBase , db : Session = Depends(get_db) , user : dict = Depends(dependecies.verify_token)):
    if not api_key.api_key:
        return JSONResponse(
            status_code=400,
            content={
                "success" : False,
                "message" : "API key is required"
            }
        )
    
    existing_user = db.query(users_model.User).filter(users_model.User.email == user['email']).first()
    existing_user.api_key = JWTutils.encrypt_api_key(api_key.api_key)
    db.commit()
    db.refresh(existing_user)
    return JSONResponse(
        status_code=200,
        content={
            "success" : True,
            "message" : "API key added successfully",
            "data": {
                "email": existing_user.email,
                "api_key": existing_user.api_key
            }
        }
    )


@app.get('/get-api-key')
def get_api_key(db : Session = Depends(get_db) , user : dict = Depends(dependecies.verify_token)):
    try:
        existing_user = db.query(users_model.User).filter(users_model.User.email == user['email']).first()
        if not existing_user:
            return JSONResponse(
                status_code=404,
                content={
                    "success" : False,
                    "message" : "User not found"
                }
            )
        
        if not existing_user.api_key:
            return JSONResponse(
                status_code=404,
                content={
                    "success" : False,
                    "message" : "API key not found"
                }
            )
        
        decrypted_api_key = JWTutils.decrypt_api_key(existing_user.api_key)
        return JSONResponse(
            status_code=200,
            content={
                "success" : True,
                "message" : "API key retrieved successfully",
                "data": {
                    "email": existing_user.email,
                    "api_key": decrypted_api_key
                }
            }
        )
    except Exception as e:
        print(f"Error retrieving API key: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success" : False,
                "message" : "Internal server error",
                "error": str(e)
            }
        )
    
@app.post("/make-user-deactivate")
def make_user_deactivate(user : dict = Depends(dependecies.verify_token) , db : Session = Depends(get_db)):
    try:
        existing_user = db.query(users_model.User).filter(users_model.User.email == user['email']).first()
        if not existing_user.is_active:
            return JSONResponse(
                status_code=404,
                content={
                    "success" : False,
                    "message" : "User is already deactivated"
                }
            )
        
        existing_user.is_active = False
        db.commit()
        db.refresh(existing_user)


        return JSONResponse(
            status_code=200,
            content={
                "success" : True,
                "message" : "User deactivated"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success" : False,
                "message" : "Internal Server Error",
                "error" : str(e)
            }
        )

@app.get('/get-current-user')
def get_current_user(payload : dict = Depends(dependecies.verify_token) , db : Session = Depends(get_db)):

    user = db.query(users_model.User).filter(users_model.User.email == payload['email']).first()
    return JSONResponse(
        status_code=200,
        content={
            "success" : True,
            "message" : "Current User Retrived",
            "data" : {
                "id" : user.id,
                "email" : user.email,
                "is_active" : user.is_active,
            }
        }
    )



main_app.include_router(app, prefix="/api/users")


