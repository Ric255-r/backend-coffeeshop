from datetime import timedelta
from fastapi import FastAPI, Security, HTTPException
from fastapi_jwt import (
    JwtAccessBearerCookie,
    JwtAuthorizationCredentials,
    JwtRefreshBearer
)

# Secret Key ini harus dirahasiakan di .env
# fastapi-jwt ga include dgn .env jd mw buat sndiri

# Read access token from bearer header and cookie (bearer priority)
access_security = JwtAccessBearerCookie(
    secret_key="testingbuatsecretkeyjwt", #value defaultnya "secret_key". ini bs di modif rupany
    auto_error=False,
    access_expires_delta=timedelta(hours=1)
)

# Read refresh token from bearer header only
refresh_security = JwtRefreshBearer(
    secret_key="testingbuatsecretkeyjwt", #value defaultnya "secret_key". ini bs di modif rupany
    auto_error=True # automatically raise HTTPException: HTTP_401_UNAUTHORIZED
)
