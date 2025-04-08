"""HTTP handler for Cloud Run."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from fitnessllm_dataplatform.batch_handler import BatchHandler
from fitnessllm_dataplatform.task_handler import Startup


class Handler(BaseHTTPRequestHandler):
    """HTTP request handler."""

    def do_POST(self) -> None:
        """Handle POST requests."""
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        # Extract required parameters
        uid = data.get("uid")
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

        if not uid or not data_source:
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {"error": "Missing required parameters: uid and data_source"}
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
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Starting server on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
