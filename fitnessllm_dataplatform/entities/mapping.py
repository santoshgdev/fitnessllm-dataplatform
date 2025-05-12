"""Mapping for OAuth2 refresh token."""

from fitnessllm_shared.streams.strava import strava_refresh_oauth_token

from fitnessllm_dataplatform.entities.enums import FitnessLLMDataSource

REFRESH_FUNCTION_MAPPING = {
    FitnessLLMDataSource.STRAVA.value: strava_refresh_oauth_token
}
