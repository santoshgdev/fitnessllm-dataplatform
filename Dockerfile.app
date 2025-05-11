FROM ${BASE_IMAGE}


ARG CACHEBUST=1
RUN echo $CACHEBUST
RUN poetry update fitnessllm-shared

#ENV PORT=8080

# Run the HTTP server
#ENTRYPOINT ["poetry", "run", "python", "-m", "fitnessllm_dataplatform.task_handler"]
