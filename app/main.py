from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from database.session import Base, engine
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn

Base.metadata.create_all(bind=engine)

main_app = FastAPI(title="Manual Testing Chatbot API")

main_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

@main_app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = {}

    for error in exc.errors():
        loc = error.get("loc", [])
        msg = error.get("msg", "Invalid input")

        # Handle missing fields
        if error["type"] == "missing" and len(loc) >= 2:
            field_name = loc[-1]
            errors[field_name] = f"{field_name.capitalize()} is required"

        # Handle missing body
        elif loc == ("body",):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Request body is required"
                }
            )

    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": "Validation error",
            "data": errors
        }
    )

@main_app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail
        }
    )