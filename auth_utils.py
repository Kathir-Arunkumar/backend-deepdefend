# auth_utils.py

import os
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from starlette.status import HTTP_401_UNAUTHORIZED
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Read the SECRET_KEY securely from the environment
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set in the .env file")

ALGORITHM = "HS256"

# This defines how FastAPI will extract the token (usually from the Authorization header)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# This function will decode the token and extract the user_id
async def get_current_user_id(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
