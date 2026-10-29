from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from datetime import date

app = Flask(__name__)
app.secret_key = "infralog-projeto-integrado"
DB_PATH = Path(__file__).with_name("banco.db")


def conectar():
    conexao = sqlite3.connect(DB_PATH)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_banco():
    with conectar() as conexao:
        conexao.executescript("""
            CREATE TABLE IF NOT EXISTS equipamento (
                id_equipamento INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                marca TEXT NOT NULL,
                modelo TEXT NOT NULL,
                numero_serie TEXT NOT NULL UNIQUE,
                hostname TEXT,
                situacao TEXT NOT NULL DEFAULT 'Disponível',
                observacao TEXT
            );

            CREATE TABLE IF NOT EXISTS colaborador (
                id_colaborador INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                setor TEXT NOT NULL,
                cargo TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS emprestimo (
                id_emprestimo INTEGER PRIMARY KEY AUTOINCREMENT,
                id_colaborador INTEGER NOT NULL,
                id_equipamento INTEGER NOT NULL,
                data_emprestimo TEXT NOT NULL,
                data_prevista_devolucao TEXT,
                data_real_devolucao TEXT,
                observacao TEXT,
                status TEXT NOT NULL DEFAULT 'Em aberto',
                FOREIGN KEY (id_colaborador) REFERENCES colaborador(id_colaborador),
                FOREIGN KEY (id_equipamento) REFERENCES equipamento(id_equipamento)
            );
        """)


@app.route("/")
def inicio():
    with conectar() as conexao:
        total = conexao.execute("SELECT COUNT(*) FROM equipamento").fetchone()[0]
        disponiveis = conexao.execute("SELECT COUNT(*) FROM equipamento WHERE situacao='Disponível'").fetchone()[0]
        emprestados = conexao.execute("SELECT COUNT(*) FROM equipamento WHERE situacao='Emprestado'").fetchone()[0]
        recentes = conexao.execute("""
            SELECT e.id_emprestimo, eq.tipo, eq.marca, eq.modelo,
                   c.nome AS colaborador, e.data_emprestimo, e.status
            FROM emprestimo e
            JOIN equipamento eq ON eq.id_equipamento=e.id_equipamento
            JOIN colaborador c ON c.id_colaborador=e.id_colaborador
            ORDER BY e.id_emprestimo DESC LIMIT 5
        """).fetchall()
    return render_template("index.html", total=total, disponiveis=disponiveis,
                           emprestados=emprestados, recentes=recentes)


@app.route("/equipamentos/novo", methods=["GET", "POST"])
def equipamento():
    if request.method == "POST":
        tipo = request.form.get("tipo", "").strip()
        marca = request.form.get("marca", "").strip()
        modelo = request.form.get("modelo", "").strip()
        numero_serie = request.form.get("numero_serie", "").strip()
        hostname = request.form.get("hostname", "").strip() or None
        observacao = request.form.get("observacao", "").strip() or None
        if not all([tipo, marca, modelo, numero_serie]):
            flash("Preencha todos os campos obrigatórios.", "erro")
            return render_template("equipamento.html", dados=request.form)
        try:
            with conectar() as conexao:
                conexao.execute("""
                    INSERT INTO equipamento
                    (tipo, marca, modelo, numero_serie, hostname, situacao, observacao)
                    VALUES (?, ?, ?, ?, ?, 'Disponível', ?)
                """, (tipo, marca, modelo, numero_serie, hostname, observacao))
            flash("Equipamento cadastrado com sucesso.", "sucesso")
            return redirect(url_for("listar_equipamentos"))
        except sqlite3.IntegrityError:
            flash("Já existe um equipamento com esse número de série.", "erro")
            return render_template("equipamento.html", dados=request.form)
    return render_template("equipamento.html", dados={})


@app.route("/equipamentos")
def listar_equipamentos():
    busca = request.args.get("busca", "").strip()
    with conectar() as conexao:
        if busca:
            termo = f"%{busca}%"
            itens = conexao.execute("""
                SELECT * FROM equipamento
                WHERE tipo LIKE ? OR marca LIKE ? OR modelo LIKE ?
                   OR numero_serie LIKE ? OR COALESCE(hostname,'') LIKE ?
                ORDER BY id_equipamento DESC
            """, (termo, termo, termo, termo, termo)).fetchall()
        else:
            itens = conexao.execute("SELECT * FROM equipamento ORDER BY id_equipamento DESC").fetchall()
    return render_template("equipamentos.html", equipamentos=itens, busca=busca)


@app.route("/colaboradores/novo", methods=["GET", "POST"])
def colaborador():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        setor = request.form.get("setor", "").strip()
        cargo = request.form.get("cargo", "").strip()
        if not all([nome, setor, cargo]):
            flash("Preencha todos os campos obrigatórios.", "erro")
            return render_template("colaborador.html", dados=request.form)
        with conectar() as conexao:
            conexao.execute("INSERT INTO colaborador (nome,setor,cargo) VALUES (?,?,?)",
                            (nome, setor, cargo))
        flash("Colaborador cadastrado com sucesso.", "sucesso")
        return redirect(url_for("listar_colaboradores"))
    return render_template("colaborador.html", dados={})


@app.route("/colaboradores")
def listar_colaboradores():
    with conectar() as conexao:
        itens = conexao.execute("SELECT * FROM colaborador ORDER BY id_colaborador DESC").fetchall()
    return render_template("colaboradores.html", colaboradores=itens)


@app.route("/emprestimos/novo", methods=["GET", "POST"])
def emprestimo():
    if request.method == "POST":
        id_colaborador = request.form.get("id_colaborador", "").strip()
        id_equipamento = request.form.get("id_equipamento", "").strip()
        data_emprestimo = request.form.get("data_emprestimo", "").strip()
        data_prevista = request.form.get("data_prevista_devolucao", "").strip() or None
        observacao = request.form.get("observacao", "").strip() or None
        if not all([id_colaborador, id_equipamento, data_emprestimo]):
            flash("Selecione o colaborador, o equipamento e a data.", "erro")
        else:
            with conectar() as conexao:
                equipamento_atual = conexao.execute(
                    "SELECT situacao FROM equipamento WHERE id_equipamento=?", (id_equipamento,)
                ).fetchone()
                if not equipamento_atual or equipamento_atual["situacao"] != "Disponível":
                    flash("O equipamento selecionado não está disponível.", "erro")
                else:
                    conexao.execute("""
                        INSERT INTO emprestimo
                        (id_colaborador,id_equipamento,data_emprestimo,
                         data_prevista_devolucao,observacao,status)
                        VALUES (?,?,?,?,?,'Em aberto')
                    """, (id_colaborador,id_equipamento,data_emprestimo,data_prevista,observacao))
                    conexao.execute("UPDATE equipamento SET situacao='Emprestado' WHERE id_equipamento=?",
                                    (id_equipamento,))
                    flash("Empréstimo registrado com sucesso.", "sucesso")
                    return redirect(url_for("listar_emprestimos"))

    with conectar() as conexao:
        colaboradores = conexao.execute("SELECT * FROM colaborador ORDER BY nome").fetchall()
        equipamentos = conexao.execute("""
            SELECT * FROM equipamento WHERE situacao='Disponível'
            ORDER BY tipo, marca, modelo
        """).fetchall()
    return render_template("emprestimo.html", colaboradores=colaboradores,
                           equipamentos=equipamentos, hoje=date.today().isoformat())


@app.route("/emprestimos")
def listar_emprestimos():
    with conectar() as conexao:
        itens = conexao.execute("""
            SELECT e.*, c.nome AS colaborador, c.setor,
                   eq.tipo, eq.marca, eq.modelo, eq.numero_serie
            FROM emprestimo e
            JOIN colaborador c ON c.id_colaborador=e.id_colaborador
            JOIN equipamento eq ON eq.id_equipamento=e.id_equipamento
            ORDER BY e.id_emprestimo DESC
        """).fetchall()
    return render_template("emprestimos.html", emprestimos=itens)


@app.post("/emprestimos/<int:id_emprestimo>/devolver")
def devolver(id_emprestimo):
    with conectar() as conexao:
        registro = conexao.execute(
            "SELECT id_equipamento,status FROM emprestimo WHERE id_emprestimo=?",
            (id_emprestimo,)
        ).fetchone()
        if not registro or registro["status"] != "Em aberto":
            flash("Esse empréstimo já foi finalizado ou não existe.", "erro")
        else:
            conexao.execute("""
                UPDATE emprestimo SET status='Finalizado', data_real_devolucao=?
                WHERE id_emprestimo=?
            """, (date.today().isoformat(), id_emprestimo))
            conexao.execute("UPDATE equipamento SET situacao='Disponível' WHERE id_equipamento=?",
                            (registro["id_equipamento"],))
            flash("Devolução registrada com sucesso.", "sucesso")
    return redirect(url_for("listar_emprestimos"))


if __name__ == "__main__":
    criar_banco()
    app.run(debug=True)
