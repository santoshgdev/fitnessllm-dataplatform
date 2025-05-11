ARG BASE_IMAGE
FROM ${BASE_IMAGE}


ARG CACHEBUST=1
RUN echo $CACHEBUST
RUN poetry add git+https://github.com/santoshgdev/fitnessllm-shared.git@main
RUN RUN poetry install --no-interaction
RUN poetry run python -c "import fitnessllm_shared; print(fitnessllm_shared.__file__)"

#ENV PORT=8080

# Run the HTTP server
#ENTRYPOINT ["poetry", "run", "python", "-m", "fitnessllm_dataplatform.task_handler"]
