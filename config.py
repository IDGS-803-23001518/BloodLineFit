from sqlalchemy import create_engine

class Config(object):
    SECRET_KEY="secretKeyBloodLineFit"
    SESSION_COCKIE_SECURE=False

class DevelopmentConfig(Config):
    DEBUG=True
    SQLALCHEMY_DATABASE_URI="mysql+pymysql://root:root@127.0.0.1/bloodlinefitDB"
    SQLALCHEMY_TRACK_MODIFICATIONS=False