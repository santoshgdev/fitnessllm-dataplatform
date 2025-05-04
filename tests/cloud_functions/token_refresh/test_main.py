import pytest
from firebase_admin import auth, delete_app, get_app
from unittest.mock import patch

from fitnessllm_dataplatform.utils.logging_utils import logger
from cloud_functions.token_refresh.main import token_refresh



def test_token_refresh_success(test_user_data, mock_request, mock_decoded_token):
    """Test successful token refresh."""
    # Mock the auth.verify_id_token function
    with patch('firebase_admin.auth.verify_id_token') as mock_verify:
        mock_verify.return_value = mock_decoded_token
        
        # Mock the strava_refresh_oauth_token function
        with patch('cloud_functions.token_refresh.main.strava_refresh_oauth_token') as mock_refresh:
            # Set up the test user data
            user_id = test_user_data["user_id"]
            mock_decoded_token["uid"] = user_id
            
            # Call the function
            response = token_refresh(mock_request)
            
            # Verify the response
            assert response.status_code == 200
            assert "Token refreshed successfully for Strava" in response.response.decode()
            
            # Verify the refresh function was called
            mock_refresh.assert_called_once()

def test_token_refresh_missing_data_source(mock_request):
    """Test token refresh with missing data source."""
    # Remove data_source from request args
    mock_request.args = {}
    
    response = token_refresh(mock_request)
    
    assert response.status_code == 400
    assert "Required data_source parameter is missing" in response.response.decode()

def test_token_refresh_invalid_token(mock_request):
    """Test token refresh with invalid token."""
    with patch('firebase_admin.auth.verify_id_token') as mock_verify:
        mock_verify.side_effect = auth.InvalidIdTokenError("Invalid token")
        
        response = token_refresh(mock_request)
        
        assert response.status_code == 401
        assert "Invalid token" in response.response.decode() 