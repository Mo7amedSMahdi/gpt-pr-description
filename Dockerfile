FROM python:3.11-slim-buster

RUN apt-get update
RUN apt-get -y install jq

COPY entrypoint.sh /action/entrypoint.sh
COPY generate_pr.py /action/generate_pr.py
COPY requirements.txt /action/requirements.txt

RUN pip3 install -r /action/requirements.txt

ENTRYPOINT ["/action/entrypoint.sh"]