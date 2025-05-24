from flask import Flask
from app import create_app

# Application initializations
app = create_app()

# settings
app.secret_key = "mysecretkey"

@app.route('/')
def index():
    return '¡Bienvenido al Sistema de Biblioteca! La aplicación se está ejecutando correctamente.'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000, debug=True)
