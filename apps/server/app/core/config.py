import os


class Settings:
    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://postgres:password@localhost:5432/livestore"
        )
        
        self.auth_token = os.getenv("AUTH_TOKEN", "insecure-token-change-me")
        self.admin_secret = os.getenv("ADMIN_SECRET", "change-me-admin-secret")
        
        # Admin user configuration
        self.admin_email = os.getenv("ADMIN_EMAIL")
        self.admin_password = os.getenv("ADMIN_PASSWORD")
        
        self.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiry_minutes = int(os.getenv("JWT_EXPIRY_MINUTES", "30"))
        
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        cors_origins_str = os.getenv("CORS_ORIGINS", "*")
        self.cors_origins = [origins.strip() for origins in cors_origins_str.split(",")]
        
        self.persistence_format_version = int(os.getenv("PERSISTENCE_FORMAT_VERSION", "7"))
        self.pull_chunk_size = int(os.getenv("PULL_CHUNK_SIZE", "100"))
        
        self.db_pool_min_size = int(os.getenv("DB_POOL_MIN_SIZE", "5"))
        self.db_pool_max_size = int(os.getenv("DB_POOL_MAX_SIZE", "20"))
        self.db_command_timeout = int(os.getenv("DB_COMMAND_TIMEOUT", "60"))
    
    def validate_database_url(self):
        if not self.database_url.startswith("postgresql"):
            raise ValueError("Only PostgreSQL is supported")
    
    @property
    def safe_database_url(self) -> str:
        url = str(self.database_url)
        if "@" in url:
            parts = url.split("@")
            return parts[0].split("://")[0] + "://***:***@" + "@".join(parts[1:])
        return url


settings = Settings()
settings.validate_database_url()