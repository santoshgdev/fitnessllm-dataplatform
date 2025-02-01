clean:
	poetry env remove --all
	poetry install --sync

build:
	docker build . -t fitnessllm-dp

run:
	docker run -it -v ${CODE_PATH}/fitnessllm-dataplatform:/app/fitnessllm-dataplatform \
				   -v /Users/santoshg/.config/gcloud:/root/.config/gcloud \
				   fitnessllm-dp:latest \
				   zsh

run_isolated:
	docker run -it fitnessllm-dp:latest zsh