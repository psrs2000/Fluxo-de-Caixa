"""
Núcleo de cálculo do Fluxo de Caixa — SEM dependência de interface.

Esta é a mesma lógica usada pela aba "Tabela Dinâmica" do programa desktop,
isolada aqui para poder ser reaproveitada por qualquer interface (Streamlit,
web, linha de comando...). Não importa PyQt5 nem nada de tela.
"""

import sqlite3
import pandas as pd

COLUNAS = ["id", "Data", "Mes", "Ano", "Categoria", "Sub_Categoria",
           "Transacao", "Descricao", "Valor"]

NOMES_MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio",
    6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro",
    11: "Novembro", 12: "Dezembro",
}

# dimensões que podem virar linha/coluna da tabela dinâmica
DIMENSOES = ["Categoria", "Sub_Categoria", "Transacao", "Mes", "Ano", "Descricao"]

AGREGACOES = ["sum", "count", "mean", "min", "max"]


def fmt_valor(v) -> str:
    """Formata no padrão brasileiro: R$ 1.234,56 (igual ao programa desktop)."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return ""
    s = f"{abs(v):,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")
    return f"-R$ {s}" if v < 0 else f"R$ {s}"


def carregar_df(caminho_db: str) -> pd.DataFrame:
    """Lê o banco SQLite do programa e devolve um DataFrame pronto para análise."""
    con = sqlite3.connect(caminho_db)
    try:
        df = pd.read_sql_query(
            "SELECT id, Data, Mes, Ano, Categoria, Sub_Categoria, Transacao,"
            " Descricao, Valor FROM registros", con)
    finally:
        con.close()

    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0)
    df["Mes"] = pd.to_numeric(df["Mes"], errors="coerce")
    df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce")
    # format="mixed" aceita datas com e sem hora na mesma coluna
    df["_DataDT"] = pd.to_datetime(df["Data"], dayfirst=True,
                                   errors="coerce", format="mixed")
    # descarta o registro-fantasma (01/01/1900) usado internamente pelo programa
    df = df[df["Ano"] != 1900]
    return df


def aplicar_filtros(df, ano=None, mes=None, categoria=None, transacao=None,
                    sub_categoria=None, de=None, ate=None, sinal="todos"):
    """Aplica os mesmos filtros de relatório da aba Tabela Dinâmica."""
    d = df
    if ano:
        d = d[d["Ano"] == int(ano)]
    if mes:
        d = d[d["Mes"] == int(mes)]
    if categoria:
        d = d[d["Categoria"] == categoria]
    if transacao:
        d = d[d["Transacao"] == transacao]
    if sub_categoria:
        d = d[d["Sub_Categoria"] == sub_categoria]
    if de is not None and ate is not None:
        d = d[(d["_DataDT"].dt.date >= de) & (d["_DataDT"].dt.date <= ate)]
    if sinal == "positivos":
        d = d[d["Valor"] > 0]
    elif sinal == "negativos":
        d = d[d["Valor"] < 0]
    return d


def _agregar(sub: pd.DataFrame, agg: str) -> float:
    """Aplica a agregação sobre um conjunto de registros."""
    if sub.empty:
        return 0.0
    if agg == "sum":
        return float(sub["Valor"].sum())
    if agg == "count":
        return float(sub["Valor"].count())
    v = getattr(sub["Valor"], agg)()
    return 0.0 if pd.isna(v) else float(v)


def montar_pivot(df, linha1, linha2=None, coluna=None, agg="sum",
                 total_geral=True):
    """Monta a tabela dinâmica e devolve um DataFrame já pronto para exibição.

    IMPORTANTE: os totais (de linha, de coluna e o Total Geral) são recalculados
    aplicando a MESMA agregação sobre o conjunto de registros correspondente.
    Somar os subtotais já agregados só seria correto para "sum" — para
    mean/min/max/count daria resultado errado. É a mesma regra do desktop.
    """
    if df.empty:
        return pd.DataFrame()

    usa_colunas = bool(coluna)
    if usa_colunas:
        valores_col = sorted(
            df[coluna].dropna().unique().tolist(),
            key=lambda x: (int(x) if str(x).lstrip("-").isdigit() else 0, str(x)))
        nomes_col = [str(c) for c in valores_col]
    else:
        valores_col, nomes_col = [None], ["Valor"]

    def celulas(sub):
        if not usa_colunas:
            return {"Valor": _agregar(sub, agg)}
        return {str(cv): _agregar(sub[sub[coluna] == cv], agg)
                for cv in valores_col}

    linhas = []
    rotulo = f"{linha1}" + (f" / {linha2}" if linha2 else "")
    for g in sorted(df[linha1].dropna().unique().tolist(), key=str):
        g_df = df[df[linha1] == g]
        registro = {rotulo: str(g), **celulas(g_df), "Total Geral": _agregar(g_df, agg)}
        linhas.append(registro)
        if linha2:
            for sg in sorted(g_df[linha2].dropna().unique().tolist(), key=str):
                sg_df = g_df[g_df[linha2] == sg]
                linhas.append({rotulo: f"    ↳ {sg}", **celulas(sg_df),
                               "Total Geral": _agregar(sg_df, agg)})

    if total_geral and linhas:
        linhas.append({rotulo: "Total Geral", **celulas(df),
                       "Total Geral": _agregar(df, agg)})

    return pd.DataFrame(linhas, columns=[rotulo] + nomes_col + ["Total Geral"])


def como_percentual(pivot: pd.DataFrame) -> pd.DataFrame:
    """Converte os valores para % do Total Geral (mesma opção do desktop)."""
    if pivot.empty:
        return pivot
    p = pivot.copy()
    total = p["Total Geral"].iloc[-1] if len(p) else 0
    if not total:
        return p
    for c in p.columns[1:]:
        p[c] = p[c] / total * 100
    return p


def resumo(df) -> dict:
    """Entradas, saídas e saldo do conjunto filtrado."""
    entradas = float(df[df["Valor"] > 0]["Valor"].sum())
    saidas = float(df[df["Valor"] < 0]["Valor"].sum())
    return {"entradas": entradas, "saidas": saidas,
            "saldo": entradas + saidas, "lancamentos": len(df)}
