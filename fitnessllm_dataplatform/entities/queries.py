from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource, FitnessLLMDataStream


def get_activities(athlete_id: str,
                   data_source: FitnessLLMDataSource,
                   data_stream: FitnessLLMDataStream):
    return f"""
        SELECT DISTINCT activity_id
        FROM dev_metrics.metrics
        WHERE athlete_id = '{athlete_id}' and data_source = '{data_source.value}' and data_stream = '{data_stream.value}'
    """
