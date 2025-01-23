import argparse
import http.server
import os
import socketserver

from jinja2 import Template


class VideoHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, video_directory: str = ".", port: int, **kwargs):
        self.video_directory = video_directory
        self.port = port
        super().__init__(*args, **kwargs)

    def log_request(self, code="-", size="-"):
        return

    def do_GET(self):
        if self.path == "/":
            videos = [
                os.path.join(self.video_directory, video_file)
                for video_file in os.listdir(self.video_directory)
                if video_file.lower().endswith((".mp4", ".avi", ".mov"))
            ]
            content = self.generate_html(videos).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            try:
                self.wfile.write(content)
            except BrokenPipeError:
                pass
        else:
            super().do_GET()

    def generate_html(self, videos):
        template_file = os.path.join(os.path.dirname(__file__), "server.html")
        with open(template_file, "r") as f:
            template = Template(f.read())
        return template.render(videos=videos, video_type=self.get_video_type)

    def get_video_type(self, video_filename):
        if video_filename.lower().endswith(".mp4"):
            return "video/mp4"
        elif video_filename.lower().endswith(".avi"):
            return "video/x-msvideo"
        elif video_filename.lower().endswith(".mov"):
            return "video/quicktime"
        return "video/mp4"  # Default type


def run_server(video_directory: str, *, port: int = 8000, verbose: bool = False):
    def handler(*args, **kwargs):
        return VideoHandler(*args, video_directory=video_directory, port=port, **kwargs)

    with socketserver.TCPServer(("", port), handler) as httpd:
        if verbose:
            print(f"Serving at port {port} from {video_directory}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            if verbose:
                print("\nShutting down the server...")
        finally:
            httpd.server_close()  # Release the port
            if verbose:
                print("Server closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Video Server")
    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        default=os.getcwd(),
        help="Directory to serve videos from (default: current directory)",
    )
    parser.add_argument(
        "-p", "--port", type=int, default=8000, help="Port to serve on (default: 8000)"
    )

    args = parser.parse_args()

    run_server(video_directory=args.directory, port=args.port)
