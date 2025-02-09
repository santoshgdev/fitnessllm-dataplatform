clean:
	poetry env remove --all
	poetry install --sync

build:
	docker build . -t fitnessllm-dp

test:
	poetry run pytest --cov --cov-branch --cov-report=html

coverage:
	coverage

run:
	docker run -it -v ${CODE_PATH}/fitnessllm-dataplatform:/app/fitnessllm-dataplatform \
				   -v ~/.config/gcloud:/root/.config/gcloud \
				   fitnessllm-dp:latest \
				   zsh

run_isolated:
	docker run -it fitnessllm-dp:latest zsh
