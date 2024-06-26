import requests
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.models.user import User
from app.schemas.user import TokenModel
from app.services.auth import auth_service

# app = FastAPI()

router = APIRouter()
templates = Jinja2Templates(directory="front/templates")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@router.get(
    "/",
    # response_model=list[PostResponse],
    # response_model=TokenModel,
    # dependencies=[Depends(RateLimiter(times=1, seconds=10))],
    name="home_page",
)
def get_home(
    request: Request,
    # body: OAuth2PasswordRequestForm = Depends(),
    # db: Session = Depends(get_db),
    # user: User = Depends(auth_service.get_current_user) ,
):
    # print(f"request = {request}")
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={},
    )
    # return templates.TemplateResponse("home.html")
    # return {"Hello": "World"}


@router.get(
    "/my_posts",
    name="my_posts_page",
    response_class=HTMLResponse,
    # response_model=TokenModel,
)
def get_my_posts(
    request: Request,
    token: str = Depends(oauth2_scheme),
    # db: Session = Depends(get_db),
    # user: User = Depends(auth_service.get_current_user),
):
    # print(f"request = {request}")
    print(f"Received token: {token}")
    from main import app

    api_path = app.url_path_for("get_posts")
    api_url = f"{request.url.scheme}://{request.url.netloc}{api_path}"
    headers = {"Authorization": f"Bearer {token}"}

    print(f"Requesting URL: {api_url}")
    print(f"Headers: {headers}")

    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code, detail="Failed to fetch posts"
        )

    return templates.TemplateResponse(
        request=request,
        name="posts_my.html",
        context={"request": request, "token": token, "posts": response.json()},
    )
    # return templates.TemplateResponse("home.html")
    # return {"Hello": "World"}


@router.get("/signup", name="signup_page")
async def signup_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="auth/signup.html", context={"request": request}
    )


@router.get("/signin", name="signin_page")
async def signin_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="auth/signin.html", context={"request": request}
    )
