"""Cloud utils specific for Strava API."""
from enum import Enum

from beartype import beartype
from cloudpathlib import GSPath

from fitnessllm_dataplatform.stream.strava.entities.enums import StravaStreams


@beartype
def get_strava_storage_path(
    bucket: Enum,
    athlete_id: str,
    strava_model: StravaStreams | None,
    **kwargs,
) -> GSPath:
    """Returns a GSPath representing a Strava storage path.

    Args:
        bucket: Bucket names reported as an Infrastructure Enum.
        athlete_id: Athlete ID
        strava_model: Specific Strava Model (Activity or other) or specific Strava Stream (heartrate, cadence, etc)
        **kwargs: Extra parameters, e.g. activity_id, used to build path

    Returns:
        GSPath object
    """
    path = f"gs://{bucket.value}/strava/athlete_id={athlete_id}/"

    if strava_model in StravaStreams and strava_model:
        path += (
            f"{strava_model.value}/{get_json_activity_name(kwargs.get('activity_id'))}"
        )
    return GSPath(path)


@beartype
def get_json_activity_name(activity_id: str | None) -> str:
    if activity_id:
        return f"activity_id={activity_id}.json"
    return ""
