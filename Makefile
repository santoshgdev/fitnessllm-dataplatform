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
	make copy_shared
	docker build . -t fitnessllm-dp

test:
	make copy_shared
	docker run -it \
	  -e POETRY_VIRTUALENVS_CREATE=false \
	  -e POETRY_NO_INTERACTION=1 \
	  -e PYTHONPATH=/app/fitnessllm-dataplatform \
	  -v "$$PWD:/app/fitnessllm-dataplatform" \
	  fitnessllm-dp:latest \
	  bash -c "cd /app/fitnessllm-dataplatform && /app/.venv/bin/pytest tests --cov --cov-branch --cov-report=html"

coverage:
	coverage

run:
	make copy_shared
	docker run -it \
	  --entrypoint /bin/bash \
	  -v "$$PWD:/app/fitnessllm-dataplatform" \
	  fitnessllm-dp:latest

lint:
	pre-commit run --all-files

repomix:
	repomix --include "**/*.json,**/*.sql,**/*.py,**/Dockerfile,**/*.yml,**/*.ini,**/*.md,**/*.toml"

copy_shared:
	for fn in cloud_functions/*; do \
		if [ -d "$$fn" ] && [ "$$(basename $$fn)" != "shared" ]; then \
			rm -rf "$$fn/shared" && \
			cp -r cloud_functions/shared "$$fn/shared"; \
		fi; \
	done
