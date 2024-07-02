from email import message
from typing import Annotated, Optional
import httpx

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from httpx import AsyncClient

from app.middlewares.middlewares import AuthMiddleware
from app.models.user import User
from app.schemas.post import PostResponse
from app.schemas.user import TokenModel
from app.services.auth import auth_service

from app.schemas.user import UserModel, UserResponse, TokenModel, RequestEmail

# app = FastAPI()

router = APIRouter()
templates = Jinja2Templates(directory="front/templates")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
# oauth2_scheme = OAuth2PasswordBearer()


async def get_token_optional(request: Request) -> Optional[str]:
    authorization: str = request.headers.get("Authorization")
    if authorization:
        scheme, token = authorization.split()
        if scheme.lower() == "bearer":
            return token
    return None


async def get_user_from_request(request: Request) -> Optional[User]:
    from main import app

    token = request.headers.get("Authorization")
    user = None
    if token:
        scheme, token = token.split()
        if scheme.lower() == "bearer":
            headers = {"authorization": f"Bearer {token}"}
            api_path = app.url_path_for("get_user")
            api_url = f"{request.url.scheme}://{request.url.netloc}{api_path}"

            print(f'"!!!!!!!!!!  {request.headers=}"')
            print(f'"!!!!!!!!!!  {headers=}"')

            async with AsyncClient() as client:
                response = await client.get(api_url, headers=headers)
                response_json = response.json()
                print(f"!!!!!!!!!!  {response_json=}")
                if response.status_code == 200:
                    user = User(**response_json)
    return user


async def log_response(response):
    print(
        f"!#F_Route - ERROR - signup user, res: \
        \n {response.status_code=}\
        \n {response.reason_phrase=}\
        \n {response.json()=}\
        \n {response.content=}\
        \n {response.text=}\
        \n {response=}"
    )


@router.get(
    "/",
    name="home_page",
)
def get_home(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={},
    )


@router.get(
    "/my_posts",
    name="my_posts_page",
    response_class=HTMLResponse,
)
async def get_my_posts_page(
    request: Request,
    token: Optional[str] = Depends(get_token_optional),
    user: Optional[User] = Depends(get_user_from_request),
):
    from main import app

    api_path = app.url_path_for("get_posts")
    api_url = f"{request.url.scheme}://{request.url.netloc}{api_path}"
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, headers=headers)
        except Exception as err:
            print(f"##### Exception {err=}")
            ...
        if response.status_code != 200:
            return templates.TemplateResponse(
                request=request,
                name="posts_my.html",
                context={
                    "request": request,
                    "message": response.json(),
                },
            )
        return templates.TemplateResponse(
            request=request,
            name="posts_my.html",
            context={
                "request": request,
                "posts": response.json(),
                "user": user,
                "is_user": True if user else False,
            },
        )
    else:
        print("_______ Not user and token")
        return templates.TemplateResponse(
            request=request,
            name="posts_my.html",
            context={
                "request": request,
                "message": {"detail": "Not authorized"},
            },
        )


@router.get(
    "/posts",
    name="posts_page",
    response_class=HTMLResponse,
)
async def get_all_posts_page(
    request: Request,
    token: Optional[str] = Depends(get_token_optional),
    user: Optional[User] = Depends(get_user_from_request),
):
    from main import app

    api_path = app.url_path_for("get_all_posts")
    api_url = f"{request.url.scheme}://{request.url.netloc}{api_path}"

    if token:
        headers = {"Authorization": f"Bearer {token}"}
    else:
        headers = request.headers

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers)
    except Exception as err:
        print("!!!!! error", err)
        return {"err": err}

    print(f"{response=}")
    if response.status_code != 200:
        return templates.TemplateResponse(
            request=request,
            name="posts.html",
            context={
                "request": request,
                "message": response,
                "user": user,
                "is_user": True if user else False,
            },
        )

    # await log_response(response)
    return templates.TemplateResponse(
        request=request,
        name="posts.html",
        context={"request": request, "posts": response.json()},
    )


@router.get(
    "/post",
    name="post_create_form_page",
    response_class=HTMLResponse,
)
async def get_create_post_page(
    request: Request,
    user: Optional[User] = Depends(get_user_from_request),
):

    return templates.TemplateResponse(
        request=request,
        name="post_create.html",
        context={"request": request, "user": user},
    )


@router.post(
    "/post",
    name="post_create_page",
    # response_class=HTMLResponse,
)
async def post_create_post_page(
    request: Request,
    description: str = Form(),
    tags: Optional[str] = Form(None),
    photo: UploadFile = File(...),
    user: Optional[User] = Depends(get_user_from_request),
):
    from main import app

    headers = {}
    is_token = False
    if "authorization" in request.headers:
        headers["Authorization"] = request.headers["Authorization"]
        is_token = True

    if is_token:
        api_path = app.url_path_for("create_post")
        api_url = f"{request.url.scheme}://{request.url.netloc}{api_path}"
        api_url = str(request.url_for("create_post"))

        file_content = await photo.read()

        params = {"description": description, "tags": tags}
        file = {"file": (photo.filename, file_content, photo.content_type)}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_url, params=params, files=file, headers=headers
            )

        response_json_py = response.json()
        if response.status_code != 201:
            print(f"create error:{response.status_code=}")
            return templates.TemplateResponse(
                request=request,
                name="post_create.html",
                context={"request": request, "message": response_json_py},
            )
        print("Return ")
        return JSONResponse(
            content=response_json_py, status_code=status.HTTP_201_CREATED
        )
    return templates.TemplateResponse(
        request=request,
        name="post_id.html",
        context={
            "request": request,
            "post": response_json_py,
            "message": {"detail": "Not authorized"},
            "user": user,
        },
    )


@router.get(
    "/posts/{post_id}",
    name="post_id_page",
)
async def get_post_page(
    post_id: int,
    request: Request,
    user: Optional[User] = Depends(get_user_from_request),
):
    from main import app

    api_path = app.url_path_for("get_post_by_id", post_id=post_id)
    api_url = f"{request.url.scheme}://{request.url.netloc}{api_path}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=request.headers)
    except Exception as err:
        return {"err": err}

    if response.status_code != 200:
        return templates.TemplateResponse(
            request=request,
            name="post_id.html",
            context={"request": request, "message": response},
        )

    return templates.TemplateResponse(
        request=request,
        name="post_id.html",
        context={
            "request": request,
            "post": response.json(),
            "user": user,
            "is_user": True if user else False,
        },
    )


@router.put(
    "/posts/{post_id}",
    name="posts_update_page",
    # response_class=HTMLResponse,
)
async def post_update_post_page(
    request: Request,
    post_id: int,
    description: str = Form(),
    tags: Optional[str] = Form(None),
    photo: UploadFile = File(default=None),
    user: Optional[User] = Depends(get_user_from_request),
):
    from main import app

    headers = {}
    is_token = False
    if "authorization" in request.headers:
        headers["Authorization"] = request.headers["Authorization"]
        is_token = True

    if is_token:

        api_path = app.url_path_for("update_post", post_id=post_id)
        api_url = f"{request.url.scheme}://{request.url.netloc}{api_path}"
        api_url = str(request.url_for("update_post", post_id=post_id))

        if True:
            print(f"############# file {photo}")
            file_content = await photo.read()
            params = {"description": description, "tags": tags}
            file = {"file": (photo.filename, file_content, photo.content_type)}
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    api_url, params=params, files=file, headers=headers
                )

        response_json_py = response.json()
        if response.status_code != 200:
            print(f"create error:{response.status_code=}")
            return templates.TemplateResponse(
                request=request,
                name="post_create.html",
                context={"request": request, "message": response_json_py},
            )
        return JSONResponse(content=response_json_py, status_code=status.HTTP_200_OK)
    return templates.TemplateResponse(
        request=request,
        name="post_id.html",
        context={
            "request": request,
            "post": response_json_py,
            "message": {"detail": "Post not update, need authorization"},
            "user": user,
        },
    )


@router.get("/signup", name="signup_form_page")
async def signup_form_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="auth/signup.html", context={"request": request}
    )


@router.post(
    "/signup",
    name="signup_post_page",
    response_model=UserResponse,
)
async def fe_signup(
    request: Request,
    firstname: Annotated[str, Form()],
    lastname: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    from main import app

    form_data = {
        "first_name": firstname,
        "last_name": lastname,
        "email": email,
        "password": password,
    }
    api_path = app.url_path_for("auth_post_signup")
    api_url = f"{request.url.scheme}://{request.url.netloc}{api_path}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=form_data)
    except Exception as err:
        print("!!!!! error", err)
        return {"err": err}
    if response.status_code != 201:
        return templates.TemplateResponse(
            request=request,
            name="auth/signup.html",
            context={"request": request, "message": response},
        )

    # redirect_url = request.app.url_path_for("home_page")
    message = "Please confirm your email, your email has been sent."
    return templates.TemplateResponse(
        request=request,
        name="auth/signin.html",
        context={"request": request, "message": message},
    )


@router.get("/signin", name="signin_form_page")
async def signin_form_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="auth/signin.html", context={"request": request}
    )


@router.post("/signin", name="signin_page")
async def signin_page(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    from main import app

    form_data = {
        "username": username,
        "password": password,
    }
    api_path = app.url_path_for("auth_signin")
    api_url = f"{request.url.scheme}://{request.url.netloc}{api_path}"

    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, data=form_data)
    if response.status_code != 200:
        return templates.TemplateResponse(
            request=request,
            name="auth/signin.html",
            context={"request": request, "message": response.json()},
        )
    response_json = response.json()
    return JSONResponse(content=response_json, status_code=status.HTTP_202_ACCEPTED)


@router.get("/resend-activation")
async def resend_activation_form(request: Request):
    return templates.TemplateResponse(
        "/auth/resend_activation.html", {"request": request}
    )


@router.get("/confirm-activation/{token}")
async def confirm_activation_form(request: Request, token: str):
    from main import app

    api_path = app.url_path_for("confirm_email_post")
    api_url = f"{request.url.scheme}://{request.url.netloc}{api_path}"

    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json={"token": token})
    if response.status_code != 200:
        print(
            response.status_code,
            response.json(),
        )
        res_json = response.json()
        message = f"Error activation email.\n{res_json}"

        return templates.TemplateResponse(
            request=request,
            name="auth/resend_activation.html",
            context={"request": request, "message": message},
        )
    # TODO проверить повторную активацию, если уже активирована
    message = "You email has been activated. Please log in."
    return templates.TemplateResponse(
        "/auth/signin.html",
        {"request": request, "message": message, "confirm": True},
    )


@router.post("/resend-activation")
async def resend_activation(request: Request, email: str = Form(...)):
    # Логика для отправки активационного письма
    from main import app

    api_path = app.url_path_for("resend_confirm_email")
    # print(f"{api_path=}")
    api_url = f"{request.url.scheme}://{request.url.netloc}{api_path}"
    # print(f"{api_url=}")

    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json={"email": email})
    if response.status_code != 200:
        # print("!!!!!!!!!!!!!!!!!!! Error starus code not 200")
        res_json = response.json()
        message = f"Error send activation email.\n{res_json}"

        return templates.TemplateResponse(
            request=request,
            name="auth/resend_activation.html",
            context={"request": request, "message": message},
        )
    message = "An activation link has been sent to your email address. Please check your inbox."
    return templates.TemplateResponse(
        "/auth/resend_activation.html", {"request": request, "message": message}
    )


@router.get("/reset-password", name="reset_password_page")
async def reset_password_form(request: Request):

    message = (
        "Enter your email address and we will send you a link to reset your password."
    )
    return templates.TemplateResponse(
        request=request,
        name="/auth/reset_password.html",
        context={"request": request, "message": message},
    )


@router.post("/reset-password")
async def reset_password(request: Request, email: str = Form(...)):
    from main import app

    api_path = app.url_path_for("forgot_password")
    # print(f"{api_path=}")
    api_url = f"{request.url.scheme}://{request.url.netloc}{api_path}"
    # print(f"{api_url=}")

    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json={"email": email})
    # TODO add if response.status_code != 200

    message = "A password reset link has been sent to your email address. Please check your inbox."
    return templates.TemplateResponse(
        "/auth/reset_password.html", context={"request": request, "message": message}
    )


@router.get("/new-password/{token}", name="new_password_page")
async def new_password(request: Request, token: str):
    message = "Enter your new password."
    return templates.TemplateResponse(
        name="auth/new_password.html",
        context={"request": request, "token": token, "message": message},
    )


@router.post("/new-password", name="enter_new_password_page")
async def enter_new_password(
    request: Request, token: str = Form(...), password: str = Form(...)
):
    print("route post /new_password", token, password)
    from main import app

    api_path = app.url_path_for("reset_password")
    # print(f"{api_path=}")
    api_url = f"{request.url.scheme}://{request.url.netloc}{api_path}"
    # print(f"{api_url=}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            api_url, json={"token": token, "password": password}
        )
    if response.status_code != 200:
        res_json = response.json()
        message = f"Error set new password.\n{res_json}"
        return templates.TemplateResponse(
            name="auth/new_password.html",
            request=request,
            context={"request": request, "token": token, "message": response.json()},
        )

    message = "Your password has been set. Please log in."
    return templates.TemplateResponse(
        "/auth/signin.html", context={"request": request, "message": message}
    )
