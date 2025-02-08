import io
from unittest.mock import MagicMock, patch

from fitnessllm_dataplatform.utils.cloud_utils import (
    create_resource_path,
    get_secret,
    write_json_to_storage,
)


def test_create_resource_path():
    project_id = "test_project"
    service = "test_service"
    name = "test_name"
    expected_path = "projects/test_project/test_service/test_name/versions/latest"
    assert create_resource_path(project_id, service, name) == expected_path


@patch.dict("os.environ", {"PROJECT_ID": "test_project"})
@patch(
    "fitnessllm_dataplatform.utils.cloud_utils.secretmanager.SecretManagerServiceClient"
)
@patch("fitnessllm_dataplatform.utils.cloud_utils.create_resource_path")
def test_get_secret(mock_create_resource_path, mock_secret_manager_client):
    mock_create_resource_path.return_value = (
        "projects/test_project/secrets/test_secret/versions/latest"
    )

    mock_client_instance = MagicMock()
    mock_secret_manager_client.return_value = mock_client_instance

    mock_response = MagicMock()
    mock_response.payload.data.decode.return_value = '{"key": "value"}'
    mock_client_instance.access_secret_version.return_value = mock_response

    secret = get_secret("test_secret")

    assert secret == {"key": "value"}
    mock_create_resource_path.assert_called_once_with(
        "test_project", "secrets", "test_secret"
    )
    mock_client_instance.access_secret_version.assert_called_once_with(
        request={"name": "projects/test_project/secrets/test_secret/versions/latest"}
    )


@patch("fitnessllm_dataplatform.utils.cloud_utils.open", new_callable=MagicMock)
def test_write_json_to_storage(mocked_open):
    fake_file = io.StringIO()
    mocked_open.return_value.__enter__.return_value = fake_file

    sample_data = {"key": "value", "numbers": [1, 2, 3]}
    fake_path = MagicMock()
    fake_path.open.return_value.__enter__.return_value = fake_file

    # Call the function with the mocked path
    write_json_to_storage(fake_path, sample_data)