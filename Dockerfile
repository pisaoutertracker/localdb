FROM python:3.11-alpine
RUN pip install PyMongo Flask flask_restful flask_testing jsonschema python-dotenv 
RUN pip install flask-cors 
RUN pip install gunicorn 
RUN pip3 install requests==2.31.0 bs4 ilock
RUN pip install Flask-PyMongo
EXPOSE 5000
WORKDIR ./localdb/deploy
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000","deploy:app"]
