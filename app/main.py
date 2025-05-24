from app import create_app
from .main import main

app = create_app()
app.register_blueprint(main)

if __name__ == "__main__":
    app.run(port=3000, debug=True)