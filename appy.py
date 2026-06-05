import streamlit as st
import pandas as pd
import numpy as np

# Configuração da Página
st.set_page_config(page_title="Iron Racers - Dimensionamento AWG", layout="wide")

# ==========================================
# 1. BASE DE DADOS (Tabelas do Anexo 1)
# ==========================================

# Tabela 42 NBR5410 - FCA (Fator de Correção por Agrupamento) - Ref 1
# Valores aproximados/interpolados conforme o documento
FCA_DICT = {
    1: 1.00, 2: 0.80, 3: 0.70, 4: 0.65, 5: 0.60, 
    6: 0.57, 7: 0.54, 8: 0.52, 9: 0.50, 12: 0.45, 
    16: 0.41, 20: 0.38
}

def obter_fca(num_circuitos):
    # Retorna o FCA adequado (arredondando para a chave mais próxima se necessário)
    chaves = sorted(list(FCA_DICT.keys()))
    for chave in chaves:
        if num_circuitos <= chave:
            return FCA_DICT[chave]
    return 0.38 # Máximo tabelado

# Tabela 40 NBR5410 - FCT (Fator de Correção por Temperatura)
FCT_PVC = {
    10: 1.22, 15: 1.17, 20: 1.12, 25: 1.06, 30: 1.00, 35: 0.94,
    40: 0.87, 45: 0.79, 50: 0.71, 55: 0.61, 60: 0.50
}

def obter_fct(temp):
    # Retorna FCT para isolação PVC (padrão)
    chaves = sorted(list(FCT_PVC.keys()))
    for chave in chaves:
        if temp <= chave:
            return FCT_PVC[chave]
    return 0.50 # Acima de 60 graus para PVC

# Tabela de Conversão AWG (Amostragem básica) e Capacidade de Corrente (Ampacidade Média PVC 30°C)
# Nota: A ampacidade real (Corrente Máxima) deve ser revisada conforme a tabela exata da NBR usada pela equipe.
AWG_DATA = pd.DataFrame([
    {"AWG": 20, "Secao_mm2": 0.5191, "Corrente_Max_A": 9.0},
    {"AWG": 18, "Secao_mm2": 0.8235, "Corrente_Max_A": 14.0},
    {"AWG": 16, "Secao_mm2": 1.307,  "Corrente_Max_A": 18.0},
    {"AWG": 14, "Secao_mm2": 2.082,  "Corrente_Max_A": 25.0},
    {"AWG": 12, "Secao_mm2": 3.307,  "Corrente_Max_A": 30.0},
    {"AWG": 10, "Secao_mm2": 5.26,   "Corrente_Max_A": 40.0},
    {"AWG": 8,  "Secao_mm2": 8.367,  "Corrente_Max_A": 55.0},
])

# ==========================================
# 2. MOTOR DE CÁLCULO
# ==========================================

def dimensionar_fio(corrente_projeto, temp, num_circuitos):
    fca = obter_fca(num_circuitos)
    fct = obter_fct(temp)
    
    # Cálculo da Corrente Corrigida: In' = In / (FCA * FCT)
    corrente_corrigida = corrente_projeto / (fca * fct)
    
    # Seleção da Bitola AWG
    bitola_selecionada = AWG_DATA[AWG_DATA['Corrente_Max_A'] >= corrente_corrigida].head(1)
    
    if not bitola_selecionada.empty:
        awg = bitola_selecionada['AWG'].values[0]
        secao = bitola_selecionada['Secao_mm2'].values[0]
    else:
        awg = "Fora de Escala (>8 AWG)"
        secao = ">8.367"
        
    return corrente_corrigida, awg, secao, fca, fct

# ==========================================
# 3. INTERFACE DO USUÁRIO (STREAMLIT)
# ==========================================

st.title("Iron Racers - Dimensionamento da Bitola de Fios")
st.markdown("Software de dimensionamento de bitolas pelo padrão **AWG** e **NBR 5410**.")

# --- HELP / TUTORIAL ---
with st.expander("Ajuda e Instruções de Uso"):
    st.write("""
    **Como utilizar o sistema:**
    1. Para verificar um único fio rapidamente, utilize o menu lateral **Cálculo Unitário**.
    2. Para dimensionar o chicote completo, faça o upload de uma planilha em **Processamento em Lote**.
    3. A planilha deve conter exatamente as colunas: "Nome do Sistema", "Componente", "Tensão de Operação", "Corrente de Projeto", "Via de Conexão", "Temperatura de Trabalho".
    """)

# --- CÁLCULO UNITÁRIO (Barra Lateral) ---
st.sidebar.header("Cálculo Unitário")
st.sidebar.markdown("Cálculo rápido para verificações pontuais.")

with st.sidebar.form("form_unitario"):
    in_corrente = st.number_input("Corrente de Projeto (A)", min_value=0.1, value=5.0, step=0.1)
    in_temp = st.number_input("Temperatura Ambiente (°C)", min_value=10, max_value=80, value=30)
    in_circ = st.number_input("Número de Circuitos Agrupados", min_value=1, max_value=20, value=1)
    
    submit_unit = st.form_submit_button("Calcular Bitola")
    
    if submit_unit:
        i_corr, awg, secao, fca, fct = dimensionar_fio(in_corrente, in_temp, in_circ)
        st.success(f"**Resultado:**")
        st.write(f"- Corrente Corrigida: **{i_corr:.2f} A**")
        st.write(f"- Fatores: FCA={fca} | FCT={fct}")
        st.write(f"- Bitola Recomendada: **{awg} AWG** ({secao} mm²)")

# --- PROCESSAMENTO EM LOTE (Tela Principal) ---
st.header("Processamento em Lote")

colunas_obrigatorias = [
    "Nome do Sistema", "Componente", "Tensão de Operação", 
    "Corrente de Projeto", "Via de Conexão", "Temperatura de Trabalho"
]

arquivo_upload = st.file_uploader("Selecione o arquivo CSV ou Excel", type=["csv", "xlsx"])

if arquivo_upload is not None:
    # Leitura do arquivo
    try:
        if arquivo_upload.name.endswith('.csv'):
            df = pd.read_csv(arquivo_upload)
        else:
            df = pd.read_excel(arquivo_upload)
            
        # Validação de Dados
        if not all(coluna in df.columns for coluna in colunas_obrigatorias):
            st.error("ERRO: O arquivo não segue o padrão. Verifique se as colunas estão corretas.")
            # Gerando template vazio para download
            template = pd.DataFrame(columns=colunas_obrigatorias)
            csv = template.to_csv(index=False).encode('utf-8')
            st.download_button("Baixar Planilha Modelo", data=csv, file_name="template_chicote.csv", mime="text/csv")
        else:
            st.success("Arquivo carregado e validado com sucesso!")
            
            # Adiciona input para número de circuitos no chicote global
            num_circ_lote = st.number_input("Circuitos agrupados neste conduto (FCA geral):", min_value=1, max_value=20, value=len(df))
            
            # Processamento
            resultados = []
            for index, row in df.iterrows():
                i_corr, awg, secao, fca, fct = dimensionar_fio(
                    row["Corrente de Projeto"], 
                    row["Temperatura de Trabalho"], 
                    num_circ_lote
                )
                resultados.append({
                    "Corrente Corrigida (A)": round(i_corr, 2),
                    "Bitola AWG": awg,
                    "Seção (mm²)": secao
                })
                
            df_resultados = pd.concat([df, pd.DataFrame(resultados)], axis=1)
            
            # Tabela de Resultados
            st.subheader("Tabela de Resultados Analítica")
            st.dataframe(df_resultados)
            
            # Botão de Exportação
            csv_export = df_resultados.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Exportar Resultados Calculados",
                data=csv_export,
                file_name="chicote_dimensionado_ironracers.csv",
                mime="text/csv",
            )
            
            # Gráfico de Distribuição de Potência
            st.subheader("Distribuição de Potência Elétrica")
            df_resultados['Potência (W)'] = df_resultados['Tensão de Operação'] * df_resultados['Corrente de Projeto']
            
            # Agrupando por Sistema
            potencia_por_sistema = df_resultados.groupby("Nome do Sistema")["Potência (W)"].sum().reset_index()
            
            st.bar_chart(data=potencia_por_sistema, x="Nome do Sistema", y="Potência (W)", color="#d9232a") # Vermelho padrão
            
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
else:
    st.info("Aguardando upload da planilha modelo para processamento em lote.")