FROM python:3.8-buster



#install requeriments
RUN pip install flask
RUN pip install requests
RUN pip install pandas

COPY ./ /app
WORKDIR  /app
EXPOSE 5000
##ENTRYPOINT [ "python", "/app/test.py" ]
# ENTRYPOINT [ "python", "/app/app.py" ]
