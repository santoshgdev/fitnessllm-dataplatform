import pytest
import os

# Set up test environment variables
os.environ['GOOGLE_CLOUD_PROJECT'] = 'your-project-id'
os.environ['FUNCTION_TARGET'] = 'refresh_token'
os.environ['FUNCTION_SOURCE'] = '.'
os.environ['FUNCTION_REGION'] = 'us-central1' 