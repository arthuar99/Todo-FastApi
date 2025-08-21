from fastapi import FastAPI, Request, status
from todoApp.models import Base
from todoApp.database import engine
from todoApp.routers import auth, todos, admin, users
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory='todoApp/templates')
app.mount("/static", StaticFiles(directory="todoApp/static"), name="static")

@app.get("/")
def test(request:Request):
    return templates.TemplateResponse("home.html" , {"request" : request})

@app.get("/healthy")
def health_check():
    return {'status': 'Healthy'}


app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(admin.router)
app.include_router(users.router)