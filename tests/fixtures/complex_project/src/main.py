"""Application entry point."""
from src.api.routes import create_app
from src.core.config import load_config
from src.services.auth import AuthService


def main():
    config = load_config()
    app = create_app(config)
    auth = AuthService(config)
    app.run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
