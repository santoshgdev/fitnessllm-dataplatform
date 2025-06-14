from fitnessllm_shared.logger_utils import structured_logger


def check_firebase_strava_data(strava_user_data: dict, **kwargs) -> None:
    """Check if the Strava user data from Firebase is complete.

    Args:
        strava_user_data: The Strava user data dictionary.

    Raises:
        ValueError: If the Strava user data is incomplete.
    """
    if strava_user_data is None:
        structured_logger.error(message="User has no Strava data",**kwargs)
        raise ValueError("User has no Strava data")
    if "athlete" not in strava_user_data or "id" not in strava_user_data["athlete"]:
        structured_logger.error("User has incomplete Strava data: missing athleteId",**kwargs)
        raise ValueError("User has incomplete Strava data: missing athlete ID")