from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    refresh_token: str = Field(validation_alias=AliasChoices('refresh_token', 'refreshToken'))


class SSOCallbackRequest(BaseModel):
    code: str


class UserInfo(BaseModel):
    id: str
    name: str
    email: str
    avatar: str | None = None


class TokenBundle(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: int
    token_type: str = 'Bearer'


class AuthResponse(BaseModel):
    user: UserInfo
    tokens: TokenBundle
