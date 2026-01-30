"""Secure API key management for PowerCV.

This module provides secure storage, retrieval, and validation of API keys
for external services (OpenAI, Cerebras, etc.).
"""

import os
import json
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Secure manager for API keys using encryption."""
    
    def __init__(self, encryption_key: Optional[str] = None, key_file: str = "api_keys.enc"):
        """Initialize API key manager.
        
        Args:
            encryption_key: Optional encryption key (if not provided, uses environment)
            key_file: Path to encrypted key storage file
        """
        self.key_file = Path(key_file)
        
        # Get or derive encryption key
        if encryption_key:
            self.encryption_key = encryption_key.encode()
        else:
            # Use environment variable or derive from machine-specific info
            env_key = os.getenv("POWERCV_ENCRYPTION_KEY")
            if env_key:
                self.encryption_key = env_key.encode()
            else:
                # Derive key from machine-specific salt (less secure but better than nothing)
                self.encryption_key = self._derive_key()
        
        # Initialize cipher
        self.cipher = Fernet(self.encryption_key)
        
        # Load existing keys
        self._keys = self._load_keys()
    
    def _derive_key(self) -> bytes:
        """Derive encryption key from machine-specific information."""
        # Use a combination of environment and system info
        salt = b"powercv_salt_2024_secure"  # In production, use a proper random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(b"powercv_default_key"))
        return key
    
    def _load_keys(self) -> Dict[str, str]:
        """Load encrypted keys from file."""
        if not self.key_file.exists():
            return {}
        
        try:
            with open(self.key_file, 'rb') as f:
                encrypted_data = f.read()
            
            if not encrypted_data:
                return {}
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Failed to load API keys: {e}")
            return {}
    
    def _save_keys(self) -> None:
        """Save encrypted keys to file."""
        try:
            data = json.dumps(self._keys).encode()
            encrypted_data = self.cipher.encrypt(data)
            
            # Ensure directory exists
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.key_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set secure permissions
            os.chmod(self.key_file, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to save API keys: {e}")
            raise
    
    def set_key(self, service: str, api_key: str) -> None:
        """Store API key for a service.
        
        Args:
            service: Service name (e.g., 'openai', 'cerebras')
            api_key: API key to store
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")
        
        self._keys[service] = api_key.strip()
        self._save_keys()
        logger.info(f"API key stored for service: {service}")
    
    def get_key(self, service: str) -> Optional[str]:
        """Retrieve API key for a service.
        
        Args:
            service: Service name
            
        Returns:
            API key or None if not found
        """
        # First try encrypted storage
        key = self._keys.get(service)
        if key:
            return key
        
        # Fallback to environment variables
        env_var_name = f"{service.upper()}_API_KEY"
        env_key = os.getenv(env_var_name)
        if env_key:
            logger.info(f"Using API key from environment for: {service}")
            return env_key
        
        logger.warning(f"API key not found for service: {service}")
        return None
    
    def delete_key(self, service: str) -> bool:
        """Delete API key for a service.
        
        Args:
            service: Service name
            
        Returns:
            True if key was deleted, False if not found
        """
        if service in self._keys:
            del self._keys[service]
            self._save_keys()
            logger.info(f"API key deleted for service: {service}")
            return True
        return False
    
    def list_services(self) -> list:
        """List all services with stored keys.
        
        Returns:
            List of service names
        """
        return list(self._keys.keys())
    
    def validate_key(self, service: str, api_key: Optional[str] = None) -> bool:
        """Validate API key format for a service.
        
        Args:
            service: Service name
            api_key: API key to validate (if None, uses stored key)
            
        Returns:
            True if key format is valid, False otherwise
        """
        if api_key is None:
            api_key = self.get_key(service)
        
        if not api_key:
            return False
        
        # Service-specific validation
        if service.lower() == "openai":
            return api_key.startswith("sk-") and len(api_key) > 40
        elif service.lower() == "cerebras":
            return len(api_key) > 20  # Basic length check
        elif service.lower() == "deepseek":
            return len(api_key) > 20  # Basic length check
        else:
            # Generic validation - non-empty and reasonable length
            return len(api_key) >= 10
    
    def rotate_key(self, service: str, new_key: str) -> bool:
        """Rotate API key for a service.
        
        Args:
            service: Service name
            new_key: New API key
            
        Returns:
            True if rotation successful, False otherwise
        """
        if not self.validate_key(service, new_key):
            raise ValueError(f"Invalid API key format for {service}")
        
        old_key = self.get_key(service)
        self.set_key(service, new_key)
        
        logger.info(f"API key rotated for service: {service}")
        return True
    
    def export_keys(self, exclude_sensitive: bool = True) -> Dict[str, str]:
        """Export keys (for backup purposes).
        
        Args:
            exclude_sensitive: If True, masks most of the key
            
        Returns:
            Dictionary of service names and (masked) keys
        """
        exported = {}
        for service, key in self._keys.items():
            if exclude_sensitive and len(key) > 8:
                # Show only first 4 and last 4 characters
                masked_key = f"{key[:4]}...{key[-4:]}"
                exported[service] = masked_key
            else:
                exported[service] = key
        
        return exported
    
    def import_keys(self, keys: Dict[str, str], overwrite: bool = False) -> None:
        """Import keys from dictionary.
        
        Args:
            keys: Dictionary of service names and API keys
            overwrite: Whether to overwrite existing keys
        """
        for service, key in keys.items():
            if service in self._keys and not overwrite:
                logger.warning(f"Skipping existing key for service: {service}")
                continue
            
            if self.validate_key(service, key):
                self.set_key(service, key)
            else:
                logger.warning(f"Invalid key format for service {service}, skipping")


# Global instance
_api_key_manager = None


def get_api_key_manager() -> APIKeyManager:
    """Get global API key manager instance."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager


def get_api_key(service: str) -> Optional[str]:
    """Convenience function to get API key for a service.
    
    Args:
        service: Service name
        
    Returns:
        API key or None if not found
    """
    manager = get_api_key_manager()
    return manager.get_key(service)


def set_api_key(service: str, api_key: str) -> None:
    """Convenience function to set API key for a service.
    
    Args:
        service: Service name
        api_key: API key to store
    """
    manager = get_api_key_manager()
    manager.set_key(service, api_key)


# Environment-based configuration
class APIKeyConfig:
    """Configuration class for API keys from environment."""
    
    @staticmethod
    def get_openai_key() -> Optional[str]:
        """Get OpenAI API key from environment."""
        return os.getenv("OPENAI_API_KEY")
    
    @staticmethod
    def get_cerebras_key() -> Optional[str]:
        """Get Cerebras API key from environment."""
        return os.getenv("CEREBRAS_API_KEY")
    
    @staticmethod
    def get_deepseek_key() -> Optional[str]:
        """Get DeepSeek API key from environment."""
        return os.getenv("DEEPSEEK_API_KEY")
    
    @staticmethod
    def validate_required_keys() -> Dict[str, bool]:
        """Validate that required API keys are present.
        
        Returns:
            Dictionary of service names and availability status
        """
        return {
            "openai": bool(APIKeyConfig.get_openai_key()),
            "cerebras": bool(APIKeyConfig.get_cerebras_key()),
            "deepseek": bool(APIKeyConfig.get_deepseek_key()),
        }


# Security utilities
def mask_api_key(api_key: str, visible_chars: int = 4) -> str:
    """Mask API key for logging.
    
    Args:
        api_key: API key to mask
        visible_chars: Number of characters to show at start and end
        
    Returns:
        Masked API key
    """
    if len(api_key) <= visible_chars * 2:
        return "*" * len(api_key)
    
    return f"{api_key[:visible_chars]}{'*' * (len(api_key) - visible_chars * 2)}{api_key[-visible_chars:]}"


def validate_api_key_format(service: str, api_key: str) -> bool:
    """Validate API key format for specific service.
    
    Args:
        service: Service name
        api_key: API key to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not api_key or not api_key.strip():
        return False
    
    service = service.lower()
    
    if service == "openai":
        # OpenAI keys start with 'sk-' and are typically 51 characters
        return api_key.startswith("sk-") and len(api_key) >= 40
    elif service == "cerebras":
        # Cerebras keys are typically alphanumeric strings
        return len(api_key) >= 20 and api_key.replace("-", "").replace("_", "").isalnum()
    elif service == "deepseek":
        # DeepSeek keys are typically alphanumeric
        return len(api_key) >= 20 and api_key.replace("-", "").replace("_", "").isalnum()
    else:
        # Generic validation
        return len(api_key) >= 10
