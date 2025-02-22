from typing import Optional, Union

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[Union[int, str]] = None


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"
