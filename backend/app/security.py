import hmac

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

_bearer = HTTPBearer(auto_error=False)


def require_deploy_token(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    expected = settings.deploy_report_token
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Deployment reporting is not configured (DEPLOY_REPORT_TOKEN missing)",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )
    supplied = credentials.credentials
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token"
        )
    return "ci"
