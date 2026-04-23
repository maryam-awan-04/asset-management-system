import os

from dotenv import load_dotenv

from app import create_app

load_dotenv()

app = create_app(os.environ.get("FLASK_CONFIG"))

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))
