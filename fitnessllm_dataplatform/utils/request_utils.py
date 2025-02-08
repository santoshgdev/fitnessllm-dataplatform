"""Request utilities."""
import requests


def handle_status_code(response: requests.models.Response) -> dict:
    """Handle status code."""
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 400:
        raise ValueError(f"Bad request: {response.text}")
    elif response.status_code == 401:
        raise PermissionError(f"Unauthorized: {response.text}")
    elif response.status_code == 403:
        raise PermissionError(f"Forbidden: {response.text}")
    elif response.status_code == 404:
        raise FileNotFoundError(f"Not found: {response.text}")
    else:
        raise Exception(
            f"Request failed with status {response.status_code}: {response.text}"
        )
