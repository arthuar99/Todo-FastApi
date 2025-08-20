from typing import Annotated
from fastapi import APIRouter , Depends , HTTPException ,Path
from sqlalchemy.orm import Session
from pydantic import BaseModel , Field

from models import Todos
from database import  SessionLocal
from starlette import status
from .auth import get_current_user



router = APIRouter()



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
db_depends = Annotated[Session,Depends(get_db)]
user_depends = Annotated[dict, Depends(get_current_user)]

class TodoRequest(BaseModel):
    title : str = Field(min_length=3)
    description: str = Field(min_length = 3 , max_length = 100)
    priority:int = Field(gt=0 , lt=6)
    complete: bool 
@router.get("/" , status_code=status.HTTP_200_OK)
async def get_all(user:user_depends,db: db_depends):
    if user is None:
         raise HTTPException(status_code=401, detail="Not authenticated")

    return db.query(Todos).all()


@router.get("/todo/{todo_id}")
async def get_todo(user : user_depends ,todo_id: int, db: db_depends):
    if user is None:
         raise HTTPException(status_code=401, detail="Not authenticated")
    todo = db.query(Todos).filter(Todos.owner_id == user.get('id')).filter(Todos.owner_id == user.get('id')).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo
 

@router.post("/todo", status_code=status.HTTP_201_CREATED)
async def create_todo(user:user_depends,todo_request: TodoRequest, db: db_depends):
    if user is None:
        raise HTTPException(status_code=401, 
                            detail="Not authenticated")
    todo_model = Todos(**todo_request.model_dump() , owner_id=user['id'])
    db.add(todo_model)
    db.commit()
    db.refresh(todo_model)
    return todo_model
  

@router.put("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(user: user_depends, db: db_depends,
                      todo_request: TodoRequest,
                      todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')

    todo_model = db.query(Todos).filter(Todos.id == todo_id)\
        .filter(Todos.owner_id == user.get('id')).first()
    if todo_model is None:
        raise HTTPException(status_code=404, detail='Todo not found.')

    todo_model.title = todo_request.title
    todo_model.description = todo_request.description
    todo_model.priority = todo_request.priority
    todo_model.complete = todo_request.complete

    db.add(todo_model)
    db.commit()


@router.delete("/todo/{todo_id}" , status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(user:user_depends,db: db_depends, todo_id:int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    todo_model = db.query(Todos).filter(Todos.id == todo_id).first()
    if todo_model is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    db.delete(todo_model)
    db.commit()
    return {"detail": "Todo deleted successfully"}


