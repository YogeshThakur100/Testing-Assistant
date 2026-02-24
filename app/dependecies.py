from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from models import users_model
from database.session import get_db
import JWTutils
import csv
import io 
import os
import logging
from pypdf import PdfReader
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
import gc
import shutil
import time
from langchain_core.prompts import ChatPromptTemplate



logger = logging.getLogger(__name__)

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

def load_pdf_data(pdf_path):
    loader = PyPDFLoader(pdf_path)
    pdf_docs = loader.load()                
    logger.info(f"📄 Loaded {len(pdf_docs)} pages from PDF")
    return pdf_docs


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extracts text from PDF bytes in memory."""
    pdf_file_object = io.BytesIO(pdf_bytes)
    reader = PdfReader(pdf_file_object)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or "" # extract_text might return None
    return text

def build_vectorstore(pdf_docs ,user_email , api_key):
    """Build a fresh vectorstore for a user, completely replacing old one"""
    
    # 1. FIRST delete any existing files on disk
    current_directory = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.abspath(os.path.join(current_directory, "Vector Store"))
    save_path = os.path.abspath(os.path.join(folder_path, user_email))
    
    # Delete old vectorstore from disk FIRST
    if os.path.exists(save_path):
        logger.warning(f"⚠️ Deleting old vectorstore: {save_path}")
        try:
            shutil.rmtree(save_path, ignore_errors=True)
            # Wait a bit to ensure files are released
            
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error deleting old vectorstore: {e}")
    
    # 2. Clear memory
    gc.collect()
    
    # 3. Prepare documents
    if pdf_docs is None:
        raise ValueError("Please provide a pdf")
    
    all_docs =  pdf_docs
    
    # 4. Split documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " "]
    )
    
    split_docs = text_splitter.split_text(all_docs)
    logger.info(f"Created {len(split_docs)} chunks for user {user_email}")

    #######################################Cost Estimation########################
    # total_embedding_tokens = 0

    # for doc in split_docs:
    #     total_embedding_tokens += estimate_cost.tokens_for_embedding(doc.page_content)

    # print(f"Estimated tokens for embedding all chunks: {total_embedding_tokens} tokens")

    # total_embedding_cost = estimate_cost.estimate_cost_for_embedding(total_embedding_tokens)
    # print(f"Estimated cost for embedding all chunks: ${total_embedding_cost:.6f}")  

    #######################################Cost Estimation########################
    
    if len(split_docs) == 0:
        logger.error("No text chunks created after splitting")
        raise ValueError("No text content extracted from documents")
    
    # 5. Create fresh embeddings and vectorstore
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small" , api_key=api_key)
        
        # Create a completely new FAISS index
        vectorstore = FAISS.from_texts(split_docs, embeddings)
        logger.info(f"Created FAISS index with {vectorstore.index.ntotal} vectors")
        
    except Exception as e:
        logger.exception(f"Error creating embeddings or FAISS index: {e}")
        raise
    
    # 6. Ensure directory exists
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        logger.info(f"📁 Created Vector Store directory: {folder_path}")
    
    # 7. Save to disk with verification
    try:
        vectorstore.save_local(save_path)
        
        # Verify the save
        if os.path.exists(os.path.join(save_path, "index.faiss")):
            logger.info(f"✅ VectorStore saved for user: {user_email}")
            logger.info(f"📍 Path: {save_path}")
        else:
            logger.error(f"❌ FAISS index file not saved properly at {save_path}")
            raise Exception("FAISS index file not saved properly")
            
    except Exception as e:
        logger.exception(f"Error saving vectorstore: {e}")
        raise
    
    # 8. Return the fresh vectorstore
    return {
        "status": "created",
    }

