setup:
	brew install pre-commit

clean:
	poetry env remove --all
	poetry install --sync

build:
	docker build . -t fitnessllm-dp

test:
	docker run -it \
	  -e POETRY_VIRTUALENVS_CREATE=false \
	  -e POETRY_NO_INTERACTION=1 \
	  -e PYTHONPATH=/app/fitnessllm-dataplatform \
	  -v "$$PWD:/app/fitnessllm-dataplatform" \
	  fitnessllm-dp:latest \
	  sh -c "cd /app/fitnessllm-dataplatform && /venv/.venv/bin/pytest --cov --cov-branch --cov-report=html"


coverage:
	coverage

run:
	docker run -it \
	  -v "$$PWD:/app/fitnessllm-dataplatform" \
	  fitnessllm-dp:latest \
	  bash

run_isolated:
	docker run -it fitnessllm-dp:latest zsh

lint:
	pre-commit run --all-files
