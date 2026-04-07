from __future__ import annotations

import uvicorn

from alphasift.app.api import create_app
from alphasift.config import load_config


def main() -> None:
    config = load_config()
    app = create_app(config)
    uvicorn.run(app, host=config.api_host, port=config.api_port)


if __name__ == "__main__":
    main()
