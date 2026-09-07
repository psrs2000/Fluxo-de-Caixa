# Protótipo web (Streamlit) — aba Tabela Dinâmica

Experimento para avaliar uma versão do **Fluxo de Caixa** rodando no navegador.
Reaproveita a lógica de cálculo do programa desktop, isolada em `nucleo.py`
(sem nenhuma dependência de PyQt5).

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

Depois é só abrir `http://localhost:8501` no navegador e **enviar o seu
`dados.db`** pela barra lateral (ou deixar o arquivo na mesma pasta).

## O que já funciona

- Filtros de relatório: Ano, Mês, Categoria, Sub-Categoria, Transação,
  período e sinal (todos / positivos / negativos)
- Estrutura da tabela: Linha 1 (grupo), Linha 2 (subgrupo), Colunas e a
  agregação (`sum`, `count`, `mean`, `min`, `max`)
- Total Geral e "Mostrar como %"
- Cores (vermelho para saída, verde para entrada) e destaque dos subtotais
- Cartões de resumo (entradas, saídas, saldo, nº de lançamentos)
- Download do resultado em CSV

Os totais são recalculados aplicando a mesma agregação sobre o conjunto de
registros correspondente — somar os subtotais só valeria para `sum` e daria
resultado errado para `mean`/`min`/`max`/`count`. É a mesma regra do desktop.

## O que ainda NÃO tem (é só um protótipo de uma aba)

Cadastro/edição de lançamentos, importação, categorias, Dashboard, Médias,
backup e senha. O programa desktop continua sendo a versão completa.

## Observação para uma versão web "de verdade"

Aqui o banco é um arquivo SQLite local. Publicado na internet, o disco do
servidor costuma ser efêmero e o acesso é de várias pessoas ao mesmo tempo —
nesse cenário o certo é trocar por um banco hospedado (ex.: PostgreSQL) e ter
login por usuário.
