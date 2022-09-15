# Dockerfile, Image, Container
FROM python:3.9

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN . /opt/venv/bin/activate

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

CMD ["python", "./main.py"]