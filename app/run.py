from main import main_app
import uvicorn

##Route imports##
from routers import users_chat
from routers import users_auth
##Route imports##


if __name__ == "__main__":
    uvicorn.run("main:main_app" , host='0.0.0.0' , port=8000 , reload=True)
