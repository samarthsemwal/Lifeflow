import os
from pathlib import Path
from dotenv import load_dotenv

basedir = Path(__file__).resolve().parent.parent
load_dotenv(basedir / '.env')

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'lifeflow-secret-key-production-default-2025')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True

    # Primary Database configuration (MySQL 8 via PyMySQL)
    DB_USER = os.getenv('DB_USER', 'lifeflow_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'lifeflow_pass')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME', 'lifeflow')

    DEFAULT_MYSQL_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    DATABASE_URL = os.getenv('DATABASE_URL', DEFAULT_MYSQL_URL)

    ALLOW_SQLITE_FALLBACK = os.getenv('ALLOW_SQLITE_FALLBACK', 'True').lower() in ('true', '1', 'yes')
    SQLITE_PATH = basedir / os.getenv('SQLITE_DB_PATH', 'lifeflow.db')
    SQLITE_URL = f"sqlite:///{SQLITE_PATH}"

    # Use specified DATABASE_URL by default
    SQLALCHEMY_DATABASE_URI = DATABASE_URL

    # Pool settings for robust connection management
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    # In testing, default to isolated in-memory or specified test DB
    TEST_DB_URL = os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:')
    SQLALCHEMY_DATABASE_URI = TEST_DB_URL
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_ENGINE_OPTIONS = {}


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    ALLOW_SQLITE_FALLBACK = False


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
