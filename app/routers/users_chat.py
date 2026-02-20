from datetime import timedelta
import json
from typing import Dict, List
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from database.session import get_db
from main import main_app
from schemas import users_chat_schema 
from models import users_chat_model , users_model
from sqlalchemy.orm import Session
import JWTutils
import dependecies
import emailFunctionality
from datetime import datetime
from langchain_core.messages import HumanMessage , AIMessage , SystemMessage
from langchain_openai import ChatOpenAI
from uuid import UUID
from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser
from openai import OpenAI

class ManualTestOutput(BaseModel):
    bdd : str
    excel_format : List[Dict[str, str]]

app = APIRouter()
parser = PydanticOutputParser(pydantic_object=ManualTestOutput)

################helper function###################

def get_user_by_email(email : str , db : Session):
    return db.query(users_model.User).filter(users_model.User.email == email).first()

def get_chat_by_chatId(chatID : str, user_id : str , db : Session):
    return db.query(users_chat_model.UserChat).filter(users_chat_model.UserChat.id == chatID , users_chat_model.UserChat.user_id == user_id).first()

def get_messages_by_chatID(chatID : UUID , db : Session):
    return db.query(users_chat_model.UserMessage).filter(users_chat_model.UserMessage.chat_id == chatID).order_by(users_chat_model.UserMessage.created_at).all()

def get_list_of_chats_by_user_id(user_id : str , db : Session):
    return db.query(users_chat_model.UserChat).filter(users_chat_model.UserChat.user_id == user_id).order_by(users_chat_model.UserChat.created_at.desc()).all()
################helper function###################

@app.post('/create-chat')
def create_chat(chat : users_chat_schema.UserChatBase , user : dict = Depends(dependecies.verify_token) , db : Session = Depends(get_db)):
    new_chat = users_chat_model.UserChat(
        user_id = user['user_id'],
        requirements = chat.requirements,
    )

    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return JSONResponse(
        status_code=200,
        content={
            "success" : True,
            "message" : "New Chat created successfully",
            "data" : {
                "chat_id" : str(new_chat.id),
                "requirements" : new_chat.requirements,
            }
        }
    )

@app.post('/{chat_id}/message')
def chat_message(chat_id : str , data : users_chat_schema.UserMessageBase , payload : dict = Depends(dependecies.verify_token) , db : Session = Depends(get_db)):
    if not chat_id:
        return JSONResponse(
            status_code=403,
            content={
                "success" : False,
                "message" : "Chat Id is not provided"
            }
        )
    
    existing_user = get_user_by_email(payload['email'] , db)
    if not existing_user.api_key:
        return JSONResponse(
            status_code=404,
            content={
                "success" : False,
                "message" : "API key is required"
            }
        )
    
    chat = get_chat_by_chatId(chat_id, payload['user_id'] , db)
    if not chat:
        return JSONResponse(
            status_code=404,
            content={
                "success" : False,
                "message" : "Chat Not Found"
            }
        )
    
    api_key = JWTutils.decrypt_api_key(existing_user.api_key)
    
    client = OpenAI(
        api_key=api_key
    )
    
    if chat.title.strip().lower() == "new chat":
        response = client.chat.completions.create(
            model = 'gpt-4o-mini',
            messages=[
                {"role" : "system" , "content" : "Generate a short, concise title (max 6 words) summarizing the user's request. Do not include quotes or extra text."},
                {"role" : "user" , "content" : data.message}
            ],
            temperature=0.5
        )
        chat.title = response.choices[0].message.content
        db.commit()
        db.refresh(chat)
    
    messages = db.query(users_chat_model.UserMessage).filter(users_chat_model.UserMessage.chat_id == chat_id).order_by(users_chat_model.UserMessage.created_at).all()

    chat_history = []

    if messages is not None:
        for msg in messages:
            if msg.role == "user":
                chat_history.append(HumanMessage(content=msg.content))
            else:
                chat_history.append(AIMessage(content=msg.content))

    format_instructions = parser.get_format_instructions()

    base_prompt = f"""
    You are a professional AI assistant designed exclusively for manual testers.

    You must generate structured manual testing artifacts only.

    You MUST generate the response strictly in valid JSON format.

    Rules:
    Return the bdd in the gherkin format
    1. The "bdd" field must contain complete BDD (Gherkin) scenarios using:
    Feature:
    Scenario:
    Given
    When
    Then
    And

    2. The "excel_format" field must contain Excel-ready manual test cases 
    with the following columns: 

    Test ID
    User Role (if applicable)
    Test Case Type (Positive / Negative / Edge / Business / End-User)
    Test Type (UI / Functional / Performance / Usability / Compatibility / Security)
    Module
    Submodule
    Title
    Test Data
    Steps
    Expected Result
    Return the excel in the proper excel format

    3. Test IDs must be sequential (TC-001, TC-002, etc.)
    4. Include positive, negative, and edge cases where applicable.
    5. Do NOT generate automation code.
    6. Do NOT generate programming scripts.
    7. Do NOT include explanations outside the JSON.
    8. Do NOT wrap the JSON in markdown.
    9. Return ONLY valid JSON.
    10. If the JSON is invalid, regenerate internally before responding.

    Global Chat Requirements:
    {chat.requirements}

    STRICT RULES:
    - Do not generate automation code
    - Do not generate programming scripts
    - Keep output business-readable

    {format_instructions}
    """


    llm = ChatOpenAI(
        model = 'gpt-4o-mini',
        temperature = 0.3,
        api_key= api_key
    )

    response = llm.invoke([
    SystemMessage(content=base_prompt),
    *chat_history,
    HumanMessage(content=data.message)
    ])

    user_msg = users_chat_model.UserMessage(
        chat_id = chat_id,
        role = "user",
        content = data.message
    )

    db.add(user_msg)

    ai_msg = users_chat_model.UserMessage(
        chat_id = chat_id,
        role = "assistant",
        content = response.content
    )

    db.add(ai_msg)

    db.commit()

    parsed_output = parser.parse(response.content)


    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": "Response received",
            "data": {
                "title" : chat.title,
                "bdd": dependecies.format_bdd(parsed_output.bdd),
                "excel_format": dependecies.convert_json_to_csv(parsed_output.excel_format)
            }
        }
    )


@app.get('/list-chats')
def list_chats(payload : dict = Depends(dependecies.verify_token) , db : Session = Depends(get_db)):
    Chats = get_list_of_chats_by_user_id(payload['user_id'] , db)

    list_of_chats = [
        {
            "chat_id" : str(chat.id),
            "title" : chat.title,
            "requirements" : chat.requirements,
            "created_at" : str(chat.created_at)
        }
        for chat in Chats
    ]
    
    return JSONResponse(
        status_code=200,
        content={
            "success" : True,
            "message" : "List of chats retrived",
            "data" : {
                "data" : list_of_chats
            }
        }
    )





@app.get('/chat_history/{chat_id}')
def chat_history_by_chat_id(
    chat_id: UUID,
    db: Session = Depends(get_db),
    payload: dict = Depends(dependecies.verify_token)
):
    chat = get_chat_by_chatId(chat_id, payload['user_id'], db)

    if not chat:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Chat not found"
            }
        )

    chat_messages = get_messages_by_chatID(chat_id, db)
    chat_history = []

    for msgs in chat_messages:

        # 🟢 USER MESSAGE
        if msgs.role == 'user':
            chat_history.append({
                "msg_id": str(msgs.id),
                "role": msgs.role,
                "content": msgs.content
            })

        # 🔵 ASSISTANT MESSAGE
        else:
            try:
                # If stored as string → parse
                if isinstance(msgs.content, str):
                    data = json.loads(msgs.content)
                else:
                    data = msgs.content

            except Exception:
                # If parsing fails, fallback safely
                data = {
                    "bdd": "",
                    "excel_format": ""
                }



            chat_history.append({
                "msg_id": str(msgs.id),
                "role": msgs.role,
                "content": {
                    "bdd" : dependecies.format_bdd(data.get('bdd')),
                    "excel_format" : dependecies.convert_json_to_csv(data.get('excel_format'))
                }
            })

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": "Chat History received",
            "data": {
                "chats": chat_history
            }
        }
    )

@app.get('/requirements/{chat_id}')
def requirements(chat_id : UUID , db : Session = Depends(get_db) , payload : dict = Depends(dependecies.verify_token)):
    chat = get_chat_by_chatId(chat_id , payload['user_id'] , db)
    if not chat:
        return JSONResponse(
            status_code=404,
            content={
                "success" : False,
                "message" : "Chat Not Found",
            }
        )
    

    return JSONResponse(
        status_code=200,
        content={
            'success' : True,
            "message" : "Chat Information received",
            "data" : {
                "title" : chat.title,
                "requirements" : chat.requirements,
                "created_at" : str(chat.created_at)
            }
        }
    )


@app.delete('/delete-chat/{chat_id}')
def delete_chat(chat_id : UUID , payload : dict = Depends(dependecies.verify_token) , db : Session = Depends(get_db)):
    print(chat_id)
    print(payload['user_id'])
    chat = get_chat_by_chatId(chat_id , payload['user_id'] , db)

    if not chat:
        return JSONResponse(
            status_code=404,
            content={
                "success" : False,
                "message" : "Chat Not Found"
            }
        )
    
    db.delete(chat)
    db.commit()

    return JSONResponse(
        status_code=200,
        content={
            "success" : True,
            "message" : "Chat deleted successfully",
            "data" : {
                "chat_id" : str(chat_id)
            }
        }
    )

@app.put('/update-chat-info/{chat_id}')
def update_chat_info(chat_id : str , chatInfo : users_chat_schema.UserChatUpdateBase , payload : dict = Depends(dependecies.verify_token) , db : Session = Depends(get_db)):
    if not chat_id:
        return JSONResponse(
            status_code=403,
            content={
                "suceess" : False,
                "message" : "Chat ID is require"
            }
        )
    
    chat = get_chat_by_chatId(chat_id , payload['user_id'] , db)
    if not chat:
        return JSONResponse(
            status_code=404,
            content={
                "success" : False,
                "message" : "Chat Not Found"
            }
        )
    
    chat.title = chatInfo.title if chatInfo.title is not None else chat.title
    chat.requirements = chatInfo.requirements if chatInfo.requirements is not None else chat.requirements

    db.commit()
    db.refresh(chat)

    return JSONResponse(
        status_code=200,
        content={
            "success" : True,
            "message" : "Information Updated",
            "data" : {
                "title" : chat.title,
                "requirements" : chat.requirements,
            }
        }
    )


main_app.include_router(app , prefix='/api/users/chat')
