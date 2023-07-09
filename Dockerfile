FROM python:3.11-slim-buster

RUN apt-get update
RUN apt-get -y install jq

COPY entrypoint.sh /action/entrypoint.sh
COPY generate_pr.py /action/generate_pr.py
COPY requirements.txt /action/requirements.txt

RUN chmod +x /action/entrypoint.sh  # Add this line to set executable permission
RUN chmod +x /action/generate_pr.py  # Add this line to set executable permission

RUN pip3 install -r /action/requirements.txt

ENTRYPOINT ["/action/entrypoint.sh"]