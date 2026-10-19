from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from dependencies import get_auth_service, get_current_user
from schemas.user import Token, UserCreate, UserResponse
from services.auth import AuthService

router = APIRouter(tags=["Авторизация"])


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             summary="Регистрация пользователя (роль USER)")
def register(data: UserCreate, service: AuthService = Depends(get_auth_service)):
    return service.register(data.username, data.password)


@router.post("/auth/login", response_model=Token, summary="Вход: получение JWT")
def login(form: OAuth2PasswordRequestForm = Depends(),
          service: AuthService = Depends(get_auth_service)):
    return Token(access_token=service.login(form.username, form.password))


@router.get("/profile", response_model=UserResponse, summary="Профиль текущего пользователя")
def profile(user=Depends(get_current_user)):
    return user
