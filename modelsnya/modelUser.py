from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

class User(BaseModel) :
    email : str
    passwd : str
    status_user: Optional[str] = Field(None)
    roles: Optional[str] = Field(None)
    # created_at
    # updated_at:

    # nama_barang: Optional[str] = Field(None)
    # harga: Optional[float] = Field(None)
    # deskripsi: Optional[str] = Field(None)

class LoginUser(BaseModel) :
    email : str
    passwd : str

# class Settings(BaseModel) :
#     authjwt_secret_key: str = "secret"

