"""HTTP handler for Cloud Run."""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from fitnessllm_dataplatform.batch_handler import BatchHandler
from fitnessllm_dataplatform.task_handler import Startup


class Handler(BaseHTTPRequestHandler):
    """HTTP request handler."""

    def extract_uid_from_token(self) -> str:
        """Extract UID from Bearer token."""
        auth_header = self.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ValueError("Missing or invalid Authorization header")
        token = auth_header.split(" ")[1]
        # Assuming the token is the UID directly, like in token_refresh
        return token

    def do_POST(self) -> None:
        """Handle POST requests."""
        try:
            # Extract UID from Bearer token
            uid = self.extract_uid_from_token()
        except ValueError as e:
            self.send_response(401)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        # Extract required parameters
        data_source = data.get("data_source")
        data_streams = data.get("data_streams")
        batch = data.get("batch", False)

        if batch:
            try:
                # Process all users
                handler = BatchHandler()
                handler.process_all_users(data_source=data_source)

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {"status": "success", "message": "Batch processing completed"}
                    ).encode()
                )
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        if not data_source:
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {"error": "Missing required parameter: data_source"}
                ).encode()
            )
            return

        try:
            # Initialize and run the task handler
            startup = Startup()
            startup.full_etl(
                uid=uid, data_source=data_source, data_streams=data_streams
            )

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())


def run_server(port: int = 8080) -> None:
    """Run the HTTP server."""
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Starting server on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
