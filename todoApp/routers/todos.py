from typing import Annotated
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from starlette import status
from todoApp.models import Todos
from todoApp.database import SessionLocal
from todoApp.routers.auth import get_current_user
from fastapi.templating import Jinja2Templates


router = APIRouter(
    prefix= '/todos',
    tags=  ['todos']
)

templates = Jinja2Templates(directory="todoApp/templates")


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
async def get_all(user: user_depends, db: db_depends):
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return db.query(Todos).filter(Todos.owner_id == user.get('id')).all()

@router.get("/todo/{todo_id}")
async def get_todo(user: user_depends, todo_id: int, db: db_depends):
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    todo = (
        db.query(Todos)
        .filter(Todos.id == todo_id)
        .filter(Todos.owner_id == user.get('id'))
        .first()
    )
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


@router.put("/todo/{todo_id}/toggle", status_code=status.HTTP_200_OK)
async def toggle_todo(user: user_depends, db: db_depends, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Not authenticated')
    todo_model = db.query(Todos).filter(Todos.id == todo_id).filter(Todos.owner_id == user.get('id')).first()
    if todo_model is None:
        raise HTTPException(status_code=404, detail='Todo not found.')
    todo_model.complete = not todo_model.complete
    db.add(todo_model)
    db.commit()
    db.refresh(todo_model)
    return {"id": todo_model.id, "complete": todo_model.complete}

@router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(user: user_depends, db: db_depends, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    todo_model = (
        db.query(Todos)
        .filter(Todos.id == todo_id)
        .filter(Todos.owner_id == user.get('id'))
        .first()
    )
    if todo_model is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    db.delete(todo_model)
    db.commit()
    return {"detail": "Todo deleted successfully"}

@router.get("/todo-page")
def render_todo_page(request: Request):
    return templates.TemplateResponse("todo.html", {"request": request})

@router.get("/edit/{todo_id}")
def render_edit_todo_page(request: Request, todo_id: int):
    return templates.TemplateResponse("edit_todo.html", {"request": request, "todo_id": todo_id})

@router.get("/view/{todo_id}")
def render_view_todo_page(request: Request, todo_id: int):
    return templates.TemplateResponse("view_todo.html", {"request": request, "todo_id": todo_id})


