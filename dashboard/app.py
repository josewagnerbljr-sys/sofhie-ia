"""
Dashboard HTML leve e 100% local.
Roda em uma porta separada do núcleo principal — acesse em http://localhost:5000
Não expõe nada para fora do seu notebook, a menos que você configure isso deliberadamente.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template
from src.database import relatorio_do_dia, init_db
from src.config import DASHBOARD_PORT

app = Flask(__name__)
init_db()


@app.route("/")
def index():
    relatorio = relatorio_do_dia()
    return render_template("index.html", relatorio=relatorio)


if __name__ == "__main__":
    print(f"Dashboard rodando em http://localhost:{DASHBOARD_PORT}")
    app.run(host="0.0.0.0", port=DASHBOARD_PORT)
