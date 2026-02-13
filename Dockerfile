FROM python:3-slim

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY import_mailbox_to_gmail.py .

ENTRYPOINT [ "python", "import_mailbox_to_gmail.py" ]
CMD [ "--help" ]
