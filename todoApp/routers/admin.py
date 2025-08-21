from typing import Annotated
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from starlette import status
from todoApp.models import Todos, Users
from todoApp.database import SessionLocal
from todoApp.routers.auth import get_current_user
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix='/admin',
    tags=['admin']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

templates = Jinja2Templates(directory="todoApp/templates")


@router.get("/dashboard")
def render_admin_dashboard(user: user_dependency, request: Request):
    if user is None or user.get('user_role') != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})


@router.get("/todo", status_code=status.HTTP_200_OK)
async def read_all(user: user_dependency, db: db_dependency):
    if user is None or user.get('user_role') != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    return db.query(Todos).all()

@router.delete("/todo/{todo_id}" , status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(user: user_dependency, db: db_dependency, todo_id:int = Path(gt=0)):
    if user is None or user.get('user_role')!= 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    todo_model = db.query(Todos).filter(Todos.id == todo_id).first()
    if todo_model is None:
         raise HTTPException(status_code=404, detail='Todo not found.')
    db.delete(todo_model)
    db.commit()


@router.get("/users", status_code=status.HTTP_200_OK)
async def list_users(user: user_dependency, db: db_dependency):
    if user is None or user.get('user_role') != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    return db.query(Users).all()


@router.get("/stats", status_code=status.HTTP_200_OK)
async def admin_stats(user: user_dependency, db: db_dependency):
    if user is None or user.get('user_role') != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    total_users = db.query(Users).count()
    total_todos = db.query(Todos).count()
    completed_todos = db.query(Todos).filter(Todos.complete == True).count()
    pending_todos = total_todos - completed_todos
    return {
        "total_users": total_users,
        "total_todos": total_todos,
        "completed_todos": completed_todos,
        "pending_todos": pending_todos
    }