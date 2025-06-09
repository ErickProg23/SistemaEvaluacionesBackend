# app/config.py
import os

class Config:
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://develop:admin123@localhost:3306/Evaluaciones"
    SQLALCHEMY_TRACK_MODIFICATIONS = False