# run.py
from app import app
from lib.webdriver_manager import WebDriverManager

if __name__ == '__main__':
    wd = WebDriverManager()
    wd.start()

    app.run(debug=True, host='0.0.0.0', port=3624)