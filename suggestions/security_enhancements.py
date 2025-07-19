"""
Security Best Practices for Portfolio Tracker
=============================================

This file demonstrates security enhancements for your cryptocurrency portfolio application.
"""

import os
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import bcrypt
import logging

# Configure security logging
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

class SecurityManager:
    """Centralized security management"""
    
    def __init__(self):
        self.secret_key = os.getenv('SECRET_KEY', self._generate_secret_key())
        self.encryption_key = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
        self.cipher_suite = Fernet(self.encryption_key)
        
    def _generate_secret_key(self) -> str:
        """Generate a secure secret key"""
        return secrets.token_urlsafe(32)
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data like API keys"""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def generate_jwt_token(self, user_id: str, expires_delta: timedelta = None) -> str:
        """Generate JWT token for authentication"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        to_encode = {"sub": user_id, "exp": expire}
        return jwt.encode(to_encode, self.secret_key, algorithm="HS256")
    
    def verify_jwt_token(self, token: str) -> Optional[str]:
        """Verify JWT token and return user_id"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            user_id: str = payload.get("sub")
            return user_id
        except jwt.PyJWTError:
            return None


class APIKeyManager:
    """Secure API key management"""
    
    def __init__(self, security_manager: SecurityManager):
        self.security = security_manager
        self.api_keys_file = "encrypted_api_keys.json"
    
    def store_api_key(self, service_name: str, api_key: str) -> bool:
        """Store API key securely"""
        try:
            encrypted_key = self.security.encrypt_sensitive_data(api_key)
            # Store in secure file or database
            # Implementation depends on your storage preference
            security_logger.info(f"API key stored for service: {service_name}")
            return True
        except Exception as e:
            security_logger.error(f"Failed to store API key: {e}")
            return False
    
    def retrieve_api_key(self, service_name: str) -> Optional[str]:
        """Retrieve and decrypt API key"""
        try:
            # Retrieve from secure storage
            # encrypted_key = get_from_storage(service_name)
            # return self.security.decrypt_sensitive_data(encrypted_key)
            pass
        except Exception as e:
            security_logger.error(f"Failed to retrieve API key: {e}")
            return None


class RateLimiter:
    """Rate limiting for API endpoints"""
    
    def __init__(self):
        self.requests = {}
        self.max_requests = 100  # per hour
        self.time_window = 3600  # 1 hour in seconds
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed based on rate limit"""
        now = datetime.now().timestamp()
        
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Remove old requests outside time window
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < self.time_window
        ]
        
        # Check if under limit
        if len(self.requests[client_ip]) < self.max_requests:
            self.requests[client_ip].append(now)
            return True
        
        return False


class InputValidator:
    """Input validation and sanitization"""
    
    @staticmethod
    def validate_portfolio_data(data: Dict[str, Any]) -> bool:
        """Validate portfolio data structure"""
        required_fields = ['balances']
        
        if not isinstance(data, dict):
            return False
        
        for field in required_fields:
            if field not in data:
                return False
        
        balances = data.get('balances', {})
        if not isinstance(balances, dict):
            return False
        
        # Validate numeric fields
        numeric_fields = ['total_usd_value', 'total_irr_value', 'total_assets']
        for field in numeric_fields:
            value = balances.get(field)
            if value is not None and not isinstance(value, (int, float)):
                return False
        
        return True
    
    @staticmethod
    def sanitize_string_input(input_str: str, max_length: int = 255) -> str:
        """Sanitize string input"""
        if not isinstance(input_str, str):
            return ""
        
        # Remove potentially dangerous characters
        sanitized = input_str.strip()[:max_length]
        # Add more sanitization as needed
        return sanitized
    
    @staticmethod
    def validate_api_key_format(api_key: str) -> bool:
        """Validate API key format"""
        if not isinstance(api_key, str):
            return False
        
        # Basic validation - adjust based on Wallex API key format
        if len(api_key) < 32 or len(api_key) > 128:
            return False
        
        # Check for valid characters (alphanumeric and common symbols)
        import re
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', api_key):
            return False
        
        return True


class SecurityMiddleware:
    """Security middleware for FastAPI"""
    
    def __init__(self, security_manager: SecurityManager, rate_limiter: RateLimiter):
        self.security = security_manager
        self.rate_limiter = rate_limiter
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'"
        }
    
    async def add_security_headers(self, request, call_next):
        """Add security headers to responses"""
        response = await call_next(request)
        
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        return response
    
    async def check_rate_limit(self, request):
        """Check rate limiting"""
        client_ip = request.client.host
        
        if not self.rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )


# Authentication dependencies for FastAPI
security_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    security_manager: SecurityManager = Depends()
) -> str:
    """Get current authenticated user"""
    token = credentials.credentials
    user_id = security_manager.verify_jwt_token(token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


class AuditLogger:
    """Security audit logging"""
    
    def __init__(self):
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)
        
        # Configure file handler for audit logs
        handler = logging.FileHandler('audit.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_api_access(self, user_id: str, endpoint: str, ip_address: str):
        """Log API access"""
        self.logger.info(
            f"API_ACCESS - User: {user_id}, Endpoint: {endpoint}, IP: {ip_address}"
        )
    
    def log_portfolio_save(self, user_id: str, portfolio_value: float):
        """Log portfolio save operations"""
        self.logger.info(
            f"PORTFOLIO_SAVE - User: {user_id}, Value: ${portfolio_value:.2f}"
        )
    
    def log_security_event(self, event_type: str, details: str, ip_address: str):
        """Log security events"""
        self.logger.warning(
            f"SECURITY_EVENT - Type: {event_type}, Details: {details}, IP: {ip_address}"
        )


class DatabaseSecurity:
    """Database security enhancements"""
    
    @staticmethod
    def create_secure_connection_string(db_path: str) -> str:
        """Create secure database connection"""
        # For SQLite, ensure proper file permissions
        import stat
        
        if os.path.exists(db_path):
            # Set restrictive permissions (owner read/write only)
            os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR)
        
        return f"sqlite:///{db_path}"
    
    @staticmethod
    def sanitize_sql_input(input_value: Any) -> Any:
        """Sanitize input for SQL queries"""
        if isinstance(input_value, str):
            # Remove SQL injection attempts
            dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]
            for char in dangerous_chars:
                input_value = input_value.replace(char, "")
        
        return input_value


# Example usage in your application:
"""
# In your main application file:

from suggestions.security_enhancements import SecurityManager, RateLimiter, AuditLogger

# Initialize security components
security_manager = SecurityManager()
rate_limiter = RateLimiter()
audit_logger = AuditLogger()

# Add to your FastAPI app
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    security_middleware = SecurityMiddleware(security_manager, rate_limiter)
    await security_middleware.check_rate_limit(request)
    return await security_middleware.add_security_headers(request, call_next)

# Protect sensitive endpoints
@app.post("/api/portfolio/save")
async def save_portfolio(
    current_user: str = Depends(get_current_user)
):
    # Your existing code here
    audit_logger.log_portfolio_save(current_user, portfolio_value)
    pass
"""

# Security checklist for implementation:
SECURITY_CHECKLIST = """
□ Implement proper authentication and authorization
□ Use HTTPS in production
□ Validate and sanitize all inputs
□ Implement rate limiting
□ Add security headers
□ Encrypt sensitive data at rest
□ Use secure session management
□ Implement audit logging
□ Regular security updates
□ Secure API key storage
□ Database security measures
□ Error handling without information disclosure
□ CORS configuration
□ Content Security Policy
□ Regular security testing
"""