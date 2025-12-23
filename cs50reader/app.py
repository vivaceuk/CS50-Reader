from flask import Flask
from cs50reader import create_app

app = create_app()
Flask.run(app)
