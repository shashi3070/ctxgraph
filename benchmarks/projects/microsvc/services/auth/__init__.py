"""Auth service module for authentication and authorization."""

from services.auth.server import AuthServiceServer, create_auth_server
from services.auth.jwt import JWTEncoder, JWTDecoder, TokenValidator
from services.auth.oauth import OAuth2Provider, OAuth2Flow, OAuth2Client
from services.auth.saml import SAMLIdentityProvider, SAMLSingleSignOn
from services.auth.models import User, Token, Session, UserRole, Permission

__all__ = [
    "AuthServiceServer", "create_auth_server",
    "JWTEncoder", "JWTDecoder", "TokenValidator",
    "OAuth2Provider", "OAuth2Flow", "OAuth2Client",
    "SAMLIdentityProvider", "SAMLSingleSignOn",
    "User", "Token", "Session", "UserRole", "Permission"
]
