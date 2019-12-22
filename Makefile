.PHONY: test

test:
	pytest

mypy:
	mypy .

lint:
	flake8 . && black --check --diff .

coverage:
	pytest --cov=tempoggl --cov-report term --cov-report html test
