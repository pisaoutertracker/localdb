import os
import sys
import importlib

sys.path.append("..")
from app.app import create_app


# add current dir to path
app = create_app('test')  # Or 'DevelopmentConfig' based on your environment

if __name__ == "__main__":
    app.run()
