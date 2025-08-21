from typing import Annotated
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from starlette import status
from todoApp.models import Users
from todoApp.database import SessionLocal
from todoApp.routers.auth import get_current_user
from passlib.context import CryptContext
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix = '/users',
    tags=['users']
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
bcrypt_context = CryptContext(schemes=['bcrypt'] , deprecated = 'auto')
templates = Jinja2Templates(directory="todoApp/templates")

class UserVerification(BaseModel):
    password:str
    new_password: str = Field(min_length=6)

@router.get('/', status_code=status.HTTP_200_OK)
async def get_user(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    return db.query(Users).filter(Users.id == user.get('id')).first()

@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(user: user_dependency, db: db_dependency, user_verification: UserVerification):
    if user is None:
          raise HTTPException(status_code=401, detail='Authentication Failed')
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()


    if not bcrypt_context.verify(user_verification.password, user_model.hashed_password):
         raise HTTPException(status_code=401, detail='Error on password change')
    user_model.hashed_password = bcrypt_context.hash(user_verification.new_password)
    db.add(user_model)
    db.commit()

@router.put("/phonenumber/{phone_number}", status_code=status.HTTP_204_NO_CONTENT)
async def change_phone_number(user : user_dependency , db: db_dependency , phone_number: str ):
    if user is None:
           raise HTTPException(status_code=401, detail='Authentication Failed')
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()
    user_model.phone_number = phone_number
    db.add(user_model)
    db.commit()
    

@router.put("/phonenumber/{phone_number}", status_code=status.HTTP_204_NO_CONTENT)
async def change_phone_number(user: user_dependency, db: db_dependency , phone_number : str):
     if user is None:
            raise HTTPException(status_code=401, detail='Authentication Failed')
     user_model = db.query(Users).filter(Users.id == user.get('id')).first()
     user_model.phone_number = phone_number
     db.add(user_model)
     db.commit()
          



@router.put('address/' , status_code=status.HTTP_204_NO_CONTENT)
async def change_address(user: user_dependency, db:db_dependency,address: str):
     if user is None:
            raise HTTPException(status_code=401, detail='Authentication Failed')
     user_model = db.query(Users).filter(Users.id == user.get('id')).first()
     user_model.address = address
     db.add(user_model)
     db.commit()

@router.get("/profile-page")
def render_profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})
          