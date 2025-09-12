"""
Secure OAuth Authentication System
Supports Google and GitHub OAuth with JWT tokens
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Request, Depends, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.requests_client import OAuth2Session
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import httpx
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secure-secret-key-change-in-production")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8003")

# Security Models
class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    provider: Optional[str] = None
    token_type: str = "access"

class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserInfo(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    provider: str
    verified: bool = False

# Security Bearer Token Handler
security = HTTPBearer(auto_error=False)

class SecureAuthSystem:
    def __init__(self):
        # Initialize OAuth client
        self.oauth = OAuth()
        self.setup_oauth_providers()
        
    def setup_oauth_providers(self):
        """Configure OAuth providers"""
        if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
            self.oauth.register(
                name='google',
                client_id=GOOGLE_CLIENT_ID,
                client_secret=GOOGLE_CLIENT_SECRET,
                server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
        
        if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:
            self.oauth.register(
                name='github',
                client_id=GITHUB_CLIENT_ID,
                client_secret=GITHUB_CLIENT_SECRET,
                access_token_url='https://github.com/login/oauth/access_token',
                access_token_params=None,
                authorize_url='https://github.com/login/oauth/authorize',
                authorize_params=None,
                api_base_url='https://api.github.com/',
                client_kwargs={'scope': 'user:email'},
            )

    def generate_secure_state(self) -> str:
        """Generate cryptographically secure state parameter"""
        return secrets.token_urlsafe(32)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create secure JWT access token"""
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": now,
            "type": "access",
            "jti": secrets.token_urlsafe(16)  # JWT ID for revocation
        })
        
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self, data: dict) -> str:
        """Create secure JWT refresh token"""
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({
            "exp": expire,
            "iat": now,
            "type": "refresh",
            "jti": secrets.token_urlsafe(16)
        })
        
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str, token_type: str = "access") -> Optional[TokenData]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Verify token type
            if payload.get("type") != token_type:
                return None
            
            # Check expiration
            exp = payload.get("exp")
            if exp is None:
                return None
            
            # Convert exp to timezone-aware datetime for comparison
            now = datetime.now(timezone.utc)
            exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
            if now > exp_dt:
                return None
            
            user_id = payload.get("sub")
            email = payload.get("email")
            provider = payload.get("provider")
            
            if user_id is None:
                return None
                
            return TokenData(
                user_id=user_id,
                email=email,
                provider=provider,
                token_type=token_type
            )
        except JWTError:
            return None

    async def get_google_user_info(self, access_token: str) -> Optional[UserInfo]:
        """Get user information from Google"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return UserInfo(
                        id=data["id"],
                        email=data["email"],
                        name=data["name"],
                        picture=data.get("picture"),
                        provider="google",
                        verified=data.get("verified_email", False)
                    )
        except Exception as e:
            print(f"Error fetching Google user info: {e}")
            return None

    async def get_github_user_info(self, access_token: str) -> Optional[UserInfo]:
        """Get user information from GitHub"""
        try:
            async with httpx.AsyncClient() as client:
                # Get user profile
                user_response = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"token {access_token}"}
                )
                
                if user_response.status_code != 200:
                    return None
                
                user_data = user_response.json()
                
                # Get primary email
                email_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"token {access_token}"}
                )
                
                primary_email = user_data.get("email")
                if email_response.status_code == 200:
                    emails = email_response.json()
                    for email in emails:
                        if email.get("primary"):
                            primary_email = email["email"]
                            break
                
                return UserInfo(
                    id=str(user_data["id"]),
                    email=primary_email or "",
                    name=user_data.get("name") or user_data.get("login"),
                    picture=user_data.get("avatar_url"),
                    provider="github",
                    verified=True  # GitHub emails are verified
                )
                
        except Exception as e:
            print(f"Error fetching GitHub user info: {e}")
            return None

    def create_auth_tokens(self, user_info: UserInfo) -> AuthTokens:
        """Create access and refresh tokens for user"""
        token_data = {
            "sub": user_info.id,
            "email": user_info.email,
            "name": user_info.name,
            "provider": user_info.provider,
            "verified": user_info.verified
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token({"sub": user_info.id, "provider": user_info.provider})
        
        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    # Demo Mode Authentication (for development)
    def create_demo_user_tokens(self, email: str, provider: str) -> AuthTokens:
        """Create demo tokens for development (when OAuth credentials not configured)"""
        demo_user = UserInfo(
            id=f"demo_{provider}_{email.replace('@', '_').replace('.', '_')}",
            email=email,
            name=f"Demo User ({provider.title()})",
            picture=None,
            provider=provider,
            verified=True
        )
        return self.create_auth_tokens(demo_user)

# Global auth system instance
auth_system = SecureAuthSystem()

# Dependency for protecting routes
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token_data = auth_system.verify_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception
    
    return token_data

# Optional authentication (returns None if not authenticated)
async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[TokenData]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    return auth_system.verify_token(credentials.credentials)