ARG BASE_IMAGE
FROM ${BASE_IMAGE}


ARG CACHEBUST=1
RUN echo $CACHEBUST
RUN poetry add git+https://github.com/santoshgdev/fitnessllm-shared.git@main

#ENV PORT=8080

# Run the HTTP server
#ENTRYPOINT ["poetry", "run", "python", "-m", "fitnessllm_dataplatform.task_handler"]
