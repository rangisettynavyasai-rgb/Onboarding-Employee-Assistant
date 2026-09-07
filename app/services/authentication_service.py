"""
Authentication Service (Phase B: Zero-Cost OIDC & Perimeter Security).
Validates Google Identity Tokens (OAuth2 ID Tokens, IAP Assertions, or Local Mock Tokens)
directly against Google Public JWKS endpoints without requiring expensive Load Balancer/WAF infrastructure.
Enforces ALLOWED_CORPORATE_DOMAIN perimeter validation to instantly drop unauthorized external requests.
"""

import logging
from typing import Optional, Dict, Any

from app.config import settings
from app.core.exceptions import AuthenticationError
from app.core.logging import log_audit_event
from app.models import AuthenticatedPrincipal

logger = logging.getLogger("patchamomma.services.auth")


class AuthenticationService:
    """Enterprise Google Authentication and Zero-Cost OIDC Token Validator."""

    def __init__(self, auth_provider: Optional[str] = None, allowed_domain: Optional[str] = None):
        self.auth_provider = auth_provider or settings.AUTH_PROVIDER
        self.allowed_corporate_domain = allowed_domain or settings.ALLOWED_CORPORATE_DOMAIN

    def authenticate_token(self, authorization_header: Optional[str]) -> AuthenticatedPrincipal:
        """
        Validates the HTTP Authorization Bearer token and enforces corporate perimeter boundaries.
        Raises AuthenticationError (401) if missing, malformed, signature invalid, or from an unauthorized domain.
        """
        if not authorization_header:
            log_audit_event("AUTH_ATTEMPT", "ANONYMOUS", "AUTHENTICATE", "DENIED", "HTTP_HEADER", {"reason": "Missing Authorization header"})
            raise AuthenticationError("Missing Authorization header. Expected 'Bearer <Google_ID_Token>'")

        parts = authorization_header.strip().split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            log_audit_event("AUTH_ATTEMPT", "ANONYMOUS", "AUTHENTICATE", "DENIED", "HTTP_HEADER", {"reason": "Malformed Authorization header"})
            raise AuthenticationError("Malformed Authorization header. Format: 'Bearer <token>'")

        token = parts[1]

        if self.auth_provider == "mock_google":
            principal = self._verify_mock_google_token(token)
        elif self.auth_provider == "google_oauth":
            principal = self._verify_google_oauth_token(token)
        elif self.auth_provider == "iap":
            principal = self._verify_iap_assertion(token)
        else:
            raise AuthenticationError(f"Unsupported authentication provider: {self.auth_provider}")

        # PERIMETER SECURITY: Enforce Corporate Domain Boundary
        self._enforce_corporate_domain(principal)
        return principal

    def _enforce_corporate_domain(self, principal: AuthenticatedPrincipal) -> None:
        """
        Perimeter Gate: Ensures the authenticated user's email or Google Workspace hosted domain
        belongs strictly to ALLOWED_CORPORATE_DOMAIN.
        """
        if not self.allowed_corporate_domain:
            return

        email_domain = principal.email.split("@")[-1].lower() if "@" in principal.email else ""
        expected_domain = self.allowed_corporate_domain.lower().lstrip("@")

        if email_domain != expected_domain:
            log_audit_event(
                "AUTH_FAILURE",
                principal.subject,
                "DOMAIN_PERIMETER_CHECK",
                "DENIED",
                principal.email,
                {"reason": "DOMAIN_MISMATCH", "expected_domain": expected_domain, "actual_email": principal.email},
            )
            raise AuthenticationError(
                f"Access denied: Corporate perimeter violation. Email '{principal.email}' does not belong to authorized domain '{expected_domain}'."
            )

        if principal.hosted_domain and principal.hosted_domain.lower() != expected_domain:
            log_audit_event(
                "AUTH_FAILURE",
                principal.subject,
                "HOSTED_DOMAIN_CHECK",
                "DENIED",
                principal.hosted_domain,
                {"reason": "HD_MISMATCH", "expected_domain": expected_domain, "actual_hd": principal.hosted_domain},
            )
            raise AuthenticationError(
                f"Access denied: Google Workspace hosted domain '{principal.hosted_domain}' does not match authorized domain '{expected_domain}'."
            )

    def _verify_mock_google_token(self, token: str) -> AuthenticatedPrincipal:
        """
        Deterministic mock verifier for local sandbox & automated CI/CD testing.
        Accepts tokens formatted as 'mock-google-token-<sub_alias>' or direct Google Subject IDs.
        """
        domain = self.allowed_corporate_domain or "company.com"

        # Explicit test token to test domain rejection
        if token.startswith("mock-google-token-unauthorized-domain") or "attacker" in token or "external" in token:
            return AuthenticatedPrincipal(
                subject="google-sub-external-999",
                email="attacker@external-domain.org",
                name="External Attacker",
                issuer="https://accounts.google.com",
                audience=settings.GOOGLE_OAUTH_CLIENT_ID,
                hosted_domain="external-domain.org",
            )

        known_mock_tokens = {
            "mock-google-token-rahul": ("google-sub-rahul-001", f"rahul.sharma@{domain}", "Rahul Sharma"),
            "mock-google-token-maya": ("google-sub-maya-002", f"maya.lin@{domain}", "Maya Lin"),
            "mock-google-token-liam": ("google-sub-liam-003", f"liam.vance@{domain}", "Liam Vance"),
            "mock-google-token-carlos": ("google-sub-carlos-004", f"carlos.s@{domain}", "Carlos Santana"),
            "mock-google-token-alex": ("google-sub-alex-005", f"alex.chen@{domain}", "Alex Chen"),
            "mock-google-token-priya": ("google-sub-priya-006", f"priya.nair@{domain}", "Priya Nair"),
            "mock-google-token-elena": ("google-sub-elena-007", f"elena.r@{domain}", "Elena Rostova"),
            "mock-google-token-marcus": ("google-sub-marcus-008", f"marcus.v@{domain}", "Marcus Vance"),
            "mock-google-token-amanda": ("google-sub-amanda-009", f"amanda.w@{domain}", "Amanda Walker"),
            "mock-google-token-sarah": ("google-sub-sarah-010", f"sarah.j@{domain}", "Sarah Jenkins"),
        }

        # Direct Google Subject token match
        if token.startswith("google-sub-"):
            alias = token.replace("google-sub-", "").split("-")[0]
            email = f"{alias}@{domain}"
            principal = AuthenticatedPrincipal(
                subject=token,
                email=email,
                name=alias.capitalize(),
                issuer="https://accounts.google.com",
                audience=settings.GOOGLE_OAUTH_CLIENT_ID,
                hosted_domain=domain,
            )
            log_audit_event("AUTH_SUCCESS", principal.subject, "VERIFY_TOKEN", "ALLOWED", "MOCK_GOOGLE", {"email": email})
            return principal

        if token in known_mock_tokens:
            sub, email, name = known_mock_tokens[token]
            principal = AuthenticatedPrincipal(
                subject=sub,
                email=email,
                name=name,
                issuer="https://accounts.google.com",
                audience=settings.GOOGLE_OAUTH_CLIENT_ID,
                hosted_domain=domain,
            )
            log_audit_event("AUTH_SUCCESS", principal.subject, "VERIFY_TOKEN", "ALLOWED", "MOCK_GOOGLE", {"email": email})
            return principal

        log_audit_event("AUTH_FAILURE", "UNKNOWN", "VERIFY_TOKEN", "DENIED", "MOCK_GOOGLE", {"token_prefix": token[:10]})
        raise AuthenticationError(f"Invalid mock Google token: '{token}'")

    def _verify_google_oauth_token(self, token: str) -> AuthenticatedPrincipal:
        """
        Zero-Cost Self-Contained OIDC Validator:
        Verifies live Google ID Token directly against Google Public JWKS endpoints
        (https://www.googleapis.com/oauth2/v3/certs) with signature, audience, issuer,
        and expiration enforcement.
        """
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests

            request = requests.Request()
            claims = id_token.verify_oauth2_token(
                token,
                request,
                audience=settings.GOOGLE_OAUTH_CLIENT_ID,
            )

            # Validate issuer
            if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
                raise AuthenticationError(f"Untrusted token issuer: {claims.get('iss')}")

            sub = claims.get("sub")
            email = claims.get("email")
            if not sub or not email:
                raise AuthenticationError("Google token missing required 'sub' or 'email' claims")

            principal = AuthenticatedPrincipal(
                subject=sub,
                email=email,
                name=claims.get("name"),
                issuer=claims.get("iss", "https://accounts.google.com"),
                audience=claims.get("aud"),
                hosted_domain=claims.get("hd"),
            )
            log_audit_event("AUTH_SUCCESS", principal.subject, "VERIFY_TOKEN", "ALLOWED", "GOOGLE_OAUTH", {"email": email})
            return principal

        except AuthenticationError:
            raise
        except Exception as e:
            logger.warning(f"Google OAuth token verification failed: {e}")
            log_audit_event("AUTH_FAILURE", "UNKNOWN", "VERIFY_TOKEN", "DENIED", "GOOGLE_OAUTH", {"error": str(e)})
            raise AuthenticationError(f"Google ID token signature verification failed: {str(e)}")

    def _verify_iap_assertion(self, token: str) -> AuthenticatedPrincipal:
        """
        Validates Cloud Identity-Aware Proxy (IAP) signed JWT if deployed behind IAP.
        """
        try:
            from google.auth.transport import requests
            from google.oauth2 import id_token

            request = requests.Request()
            claims = id_token.verify_token(
                token,
                request=request,
                certs_url="https://www.gstatic.com/iap/verify/public_key",
                audience=settings.IAP_AUDIENCE,
            )

            sub = claims.get("sub")
            email = claims.get("email")
            principal = AuthenticatedPrincipal(
                subject=sub,
                email=email,
                name=claims.get("name"),
                issuer="https://cloud.google.com/iap",
                audience=claims.get("aud"),
                hosted_domain=claims.get("hd"),
            )
            return principal
        except Exception as e:
            raise AuthenticationError(f"IAP assertion validation failed: {e}")
