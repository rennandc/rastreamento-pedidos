import requests
from bs4 import BeautifulSoup

CNPJ = "32681371006456"
NF = "33207"

url = "https://ssw.inf.br/2/resultSSW_dest_nro"

dados = {
    "cnpjdest": CNPJ,
    "NR": NF
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


def pegar_linha_depois(palavra):
    for i, linha in enumerate(linhas):
        if palavra in linha and i + 1 < len(linhas):
            return linhas[i + 1]
    return "Não encontrado"


resultado = {
    "destinatario": pegar_linha_depois("Destinatário:"),
    "nf": NF,
    "unidade": pegar_linha_depois("Unidade"),
    "data_hora": pegar_linha_depois("Data/hora"),
    "situacao": pegar_linha_depois("Situação"),
    "detalhes": ""
}

# Pega a linha maior que contém os detalhes do transporte
for linha in linhas:
    if "CT-e autorizado" in linha or "Previsao de entrega" in linha:
        resultado["detalhes"] = linha
        break

print("\nRESULTADO ORGANIZADO")
print("=" * 50)

for chave, valor in resultado.items():
    print(f"{chave}: {valor}")
