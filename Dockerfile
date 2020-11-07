FROM python:3.6

ADD . /app
WORKDIR /app

RUN pip3 install pytest
RUN pip3 install .[test]