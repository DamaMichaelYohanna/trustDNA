"""TrustDNA SDK Exception Classes."""

class TrustDNAError(Exception):
    """Base exception for all TrustDNA SDK errors."""
    pass


class AuthenticationError(TrustDNAError):
    """Raised when the Secret API key is invalid or revoked."""
    pass


class InvalidTelemetryTokenError(TrustDNAError):
    """Raised when the client telemetry token has expired or failed HMAC signature."""
    pass


class APIConnectionError(TrustDNAError):
    """Raised when the TrustDNA engine is unreachable."""
    pass
