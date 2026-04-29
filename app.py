from flask import Flask, render_template, request, flash
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
csrf = CSRFProtect(app)

@app.route("/")
def inicio():
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)