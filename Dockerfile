FROM python:3.12-alpine
RUN mkdir /usr/src/app/
COPY . /usr/src/app/
WORKDIR /usr/src/app/
EXPOSE 1200
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
