setup:
	brew install pre-commit
	curl https://pyenv.run | bash
	echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
	echo 'eval "$(pyenv init -)"' >> ~/.bashrc
	echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
	source ~/.bashrc
	pyenv install 3.12.2
	poetry install --sync

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
	  sh -c "cd /app/fitnessllm-dataplatform && /app/.venv/bin/pytest tests --cov --cov-branch --cov-report=html"

coverage:
	coverage

run:
	docker run -it \
	  -v "$$PWD:/app/fitnessllm-dataplatform" \
	  fitnessllm-dp:latest \
	  bash

lint:
	pre-commit run --all-files

repomix:
	repomix --include "**/*.json,**/*.sql,**/*.py,**/Dockerfile,**/*.yml,**/*.ini,**/*.md,**/*.toml"

cf_token_refresh:
	cd cloud_functions && functions-framework --target refresh_token --port 8080
