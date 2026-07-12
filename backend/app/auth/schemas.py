"""认证相关请求/响应 Schema。"""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool = True


class AuthResponse(BaseModel):
    user: UserInfo
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class DemoLoginRequest(BaseModel):
    """演示账号一键登录。"""
    pass
