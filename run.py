from app import create_app
import os

app = create_app()

@app.route("/test")
def home():
    return "Koyeb üzerinden Flask yayında!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    debug = os.environ.get('FLASK_ENV', 'production') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)