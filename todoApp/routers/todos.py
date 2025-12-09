from typing import Annotated
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from starlette import status
from todoApp.models import Todos
from todoApp.database import get_db # Assuming you updated this to yield AsyncSession
from todoApp.routers.auth import get_current_user
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix='/todos',
    tags=['todos']
)

templates = Jinja2Templates(directory="todoApp/templates")

# Optimized: Centralized authentication check
def get_authenticated_user(user: dict = Depends(get_current_user)):
    """Verify user is authenticated, raise 401 if not."""
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

db_depends = Annotated[Session, Depends(get_db)]
user_depends = Annotated[dict, Depends(get_authenticated_user)]


class TodoRequest(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=3, max_length=100)
    priority: int = Field(gt=0, lt=6)
    complete: bool


@router.get("/", status_code=status.HTTP_200_OK)
async def get_all(user: user_depends, db: db_depends):
    """Get all todos for the current user."""
    return db.query(Todos).filter(Todos.owner_id == user['id']).all()


@router.get("/todo/{todo_id}", status_code=status.HTTP_200_OK)
async def get_todo(user: user_depends, db: db_depends, todo_id: int = Path(gt=0)):
    """Get a specific todo by ID."""
    todo = (
        db.query(Todos)
        .filter(Todos.id == todo_id, Todos.owner_id == user['id'])
        .first()
    )
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.post("/todo", status_code=status.HTTP_201_CREATED)
async def create_todo(user: user_depends, db: db_depends, todo_request: TodoRequest):
    """Create a new todo."""
    todo_model = Todos(**todo_request.model_dump(), owner_id=user['id'])
    db.add(todo_model)
    db.commit()
    db.refresh(todo_model)
    return todo_model


@router.put("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(
    user: user_depends,
    db: db_depends,
    todo_request: TodoRequest,
    todo_id: int = Path(gt=0)
):
    """Update an existing todo."""
    todo_model = (
        db.query(Todos)
        .filter(Todos.id == todo_id, Todos.owner_id == user['id'])
        .first()
    )
    if todo_model is None:
        raise HTTPException(status_code=404, detail='Todo not found')

    # Update fields
    todo_model.title = todo_request.title
    todo_model.description = todo_request.description
    todo_model.priority = todo_request.priority
    todo_model.complete = todo_request.complete
    
    # Optimized: No need to call db.add() on already tracked object
    db.commit()


@router.put("/todo/{todo_id}/toggle", status_code=status.HTTP_200_OK)
async def toggle_todo(user: user_depends, db: db_depends, todo_id: int = Path(gt=0)):
    """Toggle todo completion status."""
    todo_model = (
        db.query(Todos)
        .filter(Todos.id == todo_id, Todos.owner_id == user['id'])
        .first()
    )
    if todo_model is None:
        raise HTTPException(status_code=404, detail='Todo not found')
    
    todo_model.complete = not todo_model.complete
    db.commit()
    # Optimized: Return without refresh since we only need these two fields
    return {"id": todo_model.id, "complete": todo_model.complete}


@router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(user: user_depends, db: db_depends, todo_id: int = Path(gt=0)):
    """Delete a todo."""
    # Optimized: Combined query and delete check
    todo_model = (
        db.query(Todos)
        .filter(Todos.id == todo_id, Todos.owner_id == user['id'])
        .first()
    )
    if todo_model is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    db.delete(todo_model)
    db.commit()
    # Note: 204 No Content should not return a body


# Frontend template routes
@router.get("/todo-page")
def render_todo_page(request: Request):
    """Render the main todo page."""
    return templates.TemplateResponse("todo.html", {"request": request})


@router.get("/edit/{todo_id}")
def render_edit_todo_page(request: Request, todo_id: int):
    """Render the edit todo page."""
    return templates.TemplateResponse("edit_todo.html", {"request": request, "todo_id": todo_id})


@router.get("/view/{todo_id}")
def render_view_todo_page(request: Request, todo_id: int):
    """Render the view todo page."""
    return templates.TemplateResponse("view_todo.html", {"request": request, "todo_id": todo_id})