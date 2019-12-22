FROM python:3.8-alpine

RUN apk add --no-cache gcc musl-dev make

ENV APP=/tempoggl

COPY requirements-dev.txt $APP/requirements-dev.txt
RUN pip install pip-tools
RUN pip-sync $APP/requirements-dev.txt

COPY . /$APP

WORKDIR $APP

CMD ["make", "lint", "test", "mypy"]
