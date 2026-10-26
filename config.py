import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'twinsentry-secret-key')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database configuration for PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'postgresql://postgres:postgres@localhost:5432/twinsentry'
    )
    
    # JWT Settings
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # Upload Settings
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app', 'static', 'uploads', 'avatars')
    MAX_CONTENT_LENGTH = 500 * 1024  # 500KB
    
    # Scheduler Settings
    SCHEDULER_API_ENABLED = True

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
