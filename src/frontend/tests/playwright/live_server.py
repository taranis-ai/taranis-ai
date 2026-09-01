import os


def main() -> None:
    socket_fd = int(os.environ["TARANIS_E2E_SOCKET_FD"])

    from werkzeug.serving import make_server

    from frontend import create_app

    app = create_app(
        {
            "DEBUG": True,
            "SERVER_NAME": os.environ["TARANIS_E2E_SERVER_NAME"],
            "TESTING": True,
        }
    )
    server = make_server("127.0.0.1", 0, app, threaded=True, fd=socket_fd)
    os.close(socket_fd)
    server.serve_forever()


if __name__ == "__main__":
    main()
