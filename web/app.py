"""
Protótipo WEB do Fluxo de Caixa — aba "Tabela Dinâmica".

Como rodar:
    pip install -r requirements.txt
    streamlit run app.py

A lógica de cálculo vem de nucleo.py (a mesma do programa desktop).
Esta é apenas a camada de tela.
"""

import os
import tempfile
import datetime

import pandas as pd
import streamlit as st

import nucleo

st.set_page_config(page_title="Fluxo de Caixa — Tabela Dinâmica",
                   page_icon="💰", layout="wide")

# ── barra lateral: de onde vêm os dados ──────────────────────────
st.sidebar.title("💰 Fluxo de Caixa")
st.sidebar.caption("Protótipo web da aba Tabela Dinâmica")

st.sidebar.subheader("Banco de dados")
arquivo = st.sidebar.file_uploader("Envie o seu dados.db", type=["db", "sqlite"])
caminho_padrao = st.sidebar.text_input(
    "…ou informe o caminho do arquivo", value="dados.db",
    help="Caminho do banco no computador onde o programa está rodando.")

caminho = None
if arquivo is not None:
    tmp = os.path.join(tempfile.gettempdir(), "fluxo_upload.db")
    with open(tmp, "wb") as f:
        f.write(arquivo.getbuffer())
    caminho = tmp
elif caminho_padrao and os.path.isfile(caminho_padrao):
    caminho = caminho_padrao

if not caminho:
    st.info("👈 Para começar, envie o arquivo **dados.db** do programa "
            "(ou informe o caminho dele) na barra lateral.")
    st.stop()

try:
    df = nucleo.carregar_df(caminho)
except Exception as e:
    st.error(f"Não consegui ler o banco de dados: {e}")
    st.stop()

if df.empty:
    st.warning("O banco não tem lançamentos.")
    st.stop()

# ── barra lateral: filtros de relatório ──────────────────────────
st.sidebar.subheader("Filtros de relatório")


def _opcoes(coluna):
    return [""] + sorted(str(v) for v in df[coluna].dropna().unique() if str(v).strip())


anos = sorted(int(a) for a in df["Ano"].dropna().unique())
f_ano = st.sidebar.selectbox("Ano", [""] + [str(a) for a in anos])
f_mes = st.sidebar.selectbox(
    "Mês", [""] + [f"{i} – {nucleo.NOMES_MESES[i]}" for i in range(1, 13)])
f_cat = st.sidebar.selectbox("Categoria", _opcoes("Categoria"))
f_sub = st.sidebar.selectbox("Sub-Categoria", _opcoes("Sub_Categoria"))
f_tran = st.sidebar.selectbox("Transação", _opcoes("Transacao"))
sinal = st.sidebar.radio("Valores", ["todos", "positivos", "negativos"],
                         horizontal=True)

usar_periodo = st.sidebar.checkbox("Filtrar por período")
de = ate = None
if usar_periodo:
    dmin = df["_DataDT"].min()
    dmax = df["_DataDT"].max()
    d1 = dmin.date() if pd.notna(dmin) else datetime.date.today()
    d2 = dmax.date() if pd.notna(dmax) else datetime.date.today()
    de = st.sidebar.date_input("De", value=d1, format="DD/MM/YYYY")
    ate = st.sidebar.date_input("Até", value=d2, format="DD/MM/YYYY")

dff = nucleo.aplicar_filtros(
    df,
    ano=f_ano or None,
    mes=(f_mes.split(" – ")[0] if f_mes else None),
    categoria=f_cat or None,
    transacao=f_tran or None,
    sub_categoria=f_sub or None,
    de=de, ate=ate, sinal=sinal,
)

# ── cabeçalho: resumo ────────────────────────────────────────────
st.title("📊 Tabela Dinâmica")

r = nucleo.resumo(dff)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Entradas", nucleo.fmt_valor(r["entradas"]))
c2.metric("Saídas", nucleo.fmt_valor(r["saidas"]))
c3.metric("Saldo", nucleo.fmt_valor(r["saldo"]))
c4.metric("Lançamentos", f"{r['lancamentos']:,}".replace(",", "."))

if dff.empty:
    st.warning("Nenhum lançamento com os filtros atuais.")
    st.stop()

# ── estrutura da tabela dinâmica ─────────────────────────────────
st.subheader("Estrutura")
e1, e2, e3, e4 = st.columns(4)
linha1 = e1.selectbox("Linha 1 (grupo)", nucleo.DIMENSOES, index=0)
linha2 = e2.selectbox("Linha 2 (subgrupo)",
                      ["(nenhuma)"] + [d for d in nucleo.DIMENSOES if d != linha1])
coluna = e3.selectbox("Colunas",
                      ["(nenhuma)"] + [d for d in nucleo.DIMENSOES if d != linha1])
agg = e4.selectbox("Agregar", nucleo.AGREGACOES, index=0)

o1, o2 = st.columns(2)
total_geral = o1.checkbox("Total Geral", value=True)
mostrar_pct = o2.checkbox("Mostrar como %", value=False)

pivot = nucleo.montar_pivot(
    dff, linha1,
    linha2=None if linha2 == "(nenhuma)" else linha2,
    coluna=None if coluna == "(nenhuma)" else coluna,
    agg=agg, total_geral=total_geral,
)

if pivot.empty:
    st.warning("Sem dados para montar a tabela.")
    st.stop()

exibir = nucleo.como_percentual(pivot) if mostrar_pct else pivot
rotulo = exibir.columns[0]
num_cols = list(exibir.columns[1:])


def _formatar(v):
    if mostrar_pct:
        return f"{v:.1f}%"
    if agg == "count":
        return f"{v:,.0f}".replace(",", ".")
    return nucleo.fmt_valor(v)


def _cor(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return ""
    if agg == "count" or mostrar_pct:
        return ""
    return "color:#c62828" if v < 0 else "color:#1b5e20"


def _destaque_linha(row):
    # Total Geral em verde-claro; grupos principais em azul-claro
    if str(row[rotulo]).strip() == "Total Geral":
        return ["background-color:#e8f5e9; font-weight:bold"] * len(row)
    if not str(row[rotulo]).startswith("    "):
        return ["background-color:#e3f2fd"] * len(row)
    return [""] * len(row)


estilo = (exibir.style
          .format({c: _formatar for c in num_cols})
          .map(_cor, subset=num_cols)
          .apply(_destaque_linha, axis=1))

st.subheader("Resultado")
st.dataframe(estilo, use_container_width=True, hide_index=True,
             height=min(700, 60 + 35 * len(exibir)))
st.caption(f"{len(pivot)} linhas  |  {len(dff):,} lançamentos  |  agregação: {agg}"
           .replace(",", "."))

# ── exportação ───────────────────────────────────────────────────
csv = pivot.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
st.download_button("⬇️ Baixar em CSV", csv, "tabela_dinamica.csv", "text/csv")
