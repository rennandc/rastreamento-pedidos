from flask import Flask, render_template, request
import pandas as pd
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTdsZGmzPU0HCTH0ysr1PFkCYt4oZbDqg8JO-MbqcD7q6RDYjAyopbd3JYDu28Y1-p3PVXEBeYN-P9S/pub?output=csv"


def limpar_numero(valor):
    return (
        str(valor)
        .replace(".", "")
        .replace("/", "")
        .replace("-", "")
        .replace(" ", "")
        .strip()
    )


def carregar_planilha():
    tabela = pd.read_csv(
        URL_PLANILHA,
        dtype=str,
        sep=None,
        engine="python",
        on_bad_lines="skip"
    )

    tabela = tabela.fillna("")
    return tabela


def buscar_pedido_na_planilha(numero_pedido):
    """
    Estrutura da planilha:
    B = CNPJ
    C = CLIENTE
    H = PEDIDO do cliente
    J = NOTA FISCAL para consultar na SSW
    """

    tabela = carregar_planilha()

    numero_digitado = str(numero_pedido).strip()

    resultado = tabela[
        tabela.iloc[:, 7].astype(str).str.contains(
            numero_digitado,
            na=False,
            regex=False
        )
    ]

    if resultado.empty:
        return None

    linha = resultado.iloc[0]

    return {
        "pedido_cliente": numero_digitado,
        "cnpj": limpar_numero(linha.iloc[1]),
        "cliente": str(linha.iloc[2]).strip(),
        "nf": str(linha.iloc[9]).strip()
    }


def buscar_cliente_por_cnpj(cnpj):
    """
    Usado na consulta manual.
    Procura o CNPJ na coluna B e retorna o cliente da coluna C.
    """

    tabela = carregar_planilha()

    cnpj_limpo = limpar_numero(cnpj)

    resultado = tabela[
        tabela.iloc[:, 1].astype(str).apply(limpar_numero) == cnpj_limpo
    ]

    if resultado.empty:
        return "Não informado"

    linha = resultado.iloc[0]
    return str(linha.iloc[2]).strip()


def consultar_ssw(cnpj, nf):
    url = "https://ssw.inf.br/2/resultSSW_dest_nro"

    dados = {
        "cnpjdest": limpar_numero(cnpj),
        "NR": str(nf).strip()
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://ssw.inf.br/2/rastreamento_dest?pwd=2",
        "Origin": "https://ssw.inf.br",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    resposta = requests.post(url, data=dados, headers=headers)

    soup = BeautifulSoup(resposta.text, "html.parser")
    texto = soup.get_text(separator="\n", strip=True)
    linhas = texto.split("\n")

    try:
        indice = linhas.index("Situação")

        unidade = linhas[indice + 3]
        data = linhas[indice + 4]
        hora = linhas[indice + 5]
        situacao = linhas[indice + 6]

        detalhes = ""

        for linha in linhas[indice + 7:]:
            if "CT-e autorizado" in linha or "Previsao de entrega" in linha:
                detalhes = linha
                break

        return {
            "cnpj": limpar_numero(cnpj),
            "nf": str(nf).strip(),
            "unidade": unidade,
            "data_hora": f"{data} {hora}",
            "situacao": situacao,
            "detalhes": detalhes if detalhes else "Detalhes não encontrados."
        }

    except Exception:
        return {
            "cnpj": limpar_numero(cnpj),
            "nf": str(nf).strip(),
            "unidade": "Não encontrado",
            "data_hora": "Não encontrado",
            "situacao": "Rastreamento não encontrado",
            "detalhes": "Não foi possível localizar os dados na SSW."
        }


@app.route("/", methods=["GET", "POST"])
def home():
    resultado = None
    mensagem = None

    if request.method == "POST":
        tipo_consulta = request.form.get("tipo_consulta")

        try:
            if tipo_consulta == "pedido":
                numero_pedido = request.form.get("pedido")

                if not numero_pedido:
                    mensagem = "Informe o número do pedido."
                else:
                    pedido = buscar_pedido_na_planilha(numero_pedido)

                    if pedido is None:
                        mensagem = "Pedido não encontrado na planilha."
                    else:
                        resultado = consultar_ssw(pedido["cnpj"], pedido["nf"])
                        resultado["pedido"] = pedido["pedido_cliente"]
                        resultado["cliente"] = pedido["cliente"]

            elif tipo_consulta == "manual":
                cnpj = request.form.get("cnpj")
                nf = request.form.get("nf")

                if not cnpj or not nf:
                    mensagem = "Informe CNPJ e NF."
                else:
                    resultado = consultar_ssw(cnpj, nf)
                    resultado["pedido"] = "Consulta manual"
                    resultado["cliente"] = buscar_cliente_por_cnpj(cnpj)

        except Exception as erro:
            mensagem = f"Erro ao consultar: {erro}"

    return render_template("index.html", resultado=resultado, mensagem=mensagem)


if __name__ == "__main__":
    app.run(debug=True)