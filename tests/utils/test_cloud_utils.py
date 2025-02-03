import io
import json
from unittest.mock import MagicMock, patch

from fitnessllm_dataplatform.utils.cloud_utils import create_resource_path, get_secret, write_json_to_storage


def test_create_resource_path():
    project_id = "test_project"
    service = "test_service"
    name = "test_name"
    expected_path = "projects/test_project/test_service/test_name/versions/latest"
    assert create_resource_path(project_id, service, name) == expected_path

@patch.dict('os.environ', {'PROJECT_ID': 'test_project'})
@patch('fitnessllm_dataplatform.utils.cloud_utils.secretmanager.SecretManagerServiceClient')
@patch('fitnessllm_dataplatform.utils.cloud_utils.create_resource_path')
def test_get_secret(mock_create_resource_path, mock_secret_manager_client):
    mock_create_resource_path.return_value = 'projects/test_project/secrets/test_secret/versions/latest'

    mock_client_instance = MagicMock()
    mock_secret_manager_client.return_value = mock_client_instance

    mock_response = MagicMock()
    mock_response.payload.data.decode.return_value = '{"key": "value"}'
    mock_client_instance.access_secret_version.return_value = mock_response

    secret = get_secret('test_secret')

    assert secret == {"key": "value"}
    mock_create_resource_path.assert_called_once_with('test_project', 'secrets', 'test_secret')
    mock_client_instance.access_secret_version.assert_called_once_with(
        request={"name": 'projects/test_project/secrets/test_secret/versions/latest'}
    )


@patch('fitnessllm_dataplatform.utils.cloud_utils.json.dump')
def test_write_json_to_storage(mocked_json_dump):
    fake_file = io.StringIO()
    fake_path = MagicMock()

    sample_data = {"key": "value", "numbers": [1, 2, 3]}

    # Call the function with the mocked path
    write_json_to_storage(fake_path, sample_data)

    # Rewind the fake file to read from the beginning
    fake_file.seek(0)
    written_data = json.load(fake_file)

    # Assert the data was written as expected without actual disk I/O
    assert written_data == sample_data