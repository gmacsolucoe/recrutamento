import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
import plotly.express as px
import re
import time
import openai
import json
import os
from datetime import date

# --- Configurações da API OpenAI ---
openai.api_key = st.secrets["openai_api_key"]

st.set_page_config(page_title="Analisador Virtual - Big Tech RHday", layout="wide")

# --- Funções de Salvar e Carregar Dados ---
def salvar_dados_analisados(df):
    try:
        df.to_json("analise_salva.json", orient="records", date_format="iso")
        return True
    except Exception as e:
        st.error(f"Erro ao salvar o arquivo: {e}")
        return False

def carregar_dados_analisados():
    if os.path.exists("analise_salva.json"):
        try:
            df = pd.read_json("analise_salva.json", orient="records")
            df['Data de Upload'] = pd.to_datetime(df['Data de Upload']).dt.date
            return df
        except Exception as e:
            st.error(f"Erro ao carregar o arquivo salvo: {e}")
            return pd.DataFrame()
    return pd.DataFrame()


# --- Inicialização do estado da sessão ---
if "df_analise" not in st.session_state:
    st.session_state["df_analise"] = carregar_dados_analisados()

if "arquivos" not in st.session_state:
    st.session_state["arquivos"] = []


menu = st.sidebar.radio(
    "Menu",
    ["🏠 Home", "🏷️ Upload Currículos", "🚀 Analisador Excellence Big Tech", "📅 RHday"]
)

# --- Palavras-chave para pontuação e análise (você pode editar aqui) ---
Habilidades_Chave = {
    "Python": 20, "SQL": 20, "Excel": 10, "Power BI": 15, "Logística": 5,
    "Dados": 10, "Análise": 10, "Marketing": 5, "Vendas": 5, "Atendimento": 5, "RH": 5
}
Certificacoes_Chave = {
    "PMP": 15, "Scrum": 10, "AWS": 20, "AZ-900": 10, "Google Cloud": 15
}

# --- Função para salvar arquivos permanentemente ---
def salvar_curriculos(arquivos):
    folder_path = "curriculos_salvos"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    saved_count = 0
    for arquivo in arquivos:
        file_path = os.path.join(folder_path, arquivo.name)
        with open(file_path, "wb") as f:
            f.write(arquivo.getbuffer())
        saved_count += 1
    st.success(f"✅ {saved_count} arquivo(s) salvo(s) permanentemente na pasta '{folder_path}'!")


# --- Função para analisar currículo (Método Híbrido: IA + Código) ---
def analisar_curriculo(texto_curriculo):
    prompt_detalhado = f"""
    Analise o currículo a seguir e forneça uma avaliação detalhada em tópicos.
    O objetivo é criar um parecer de recrutador que cubra os seguintes pontos:
    1. Resumo Profissional: Um parágrafo avaliando o perfil do candidato.
    2. Destaques: Liste os pontos fortes e diferenciais do candidato (experiência, habilidades).
    3. Oportunidades: Liste áreas onde o candidato poderia se desenvolver ou adquirir novas habilidades.
    4. Relevância para a Vaga: Um comentário sobre o quão alinhado o perfil está com uma vaga de tecnologia em uma Big Tech, como Google, Amazon ou Meta.

    Currículo:
    {texto_curriculo[:4000]}
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente de RH. Forneça uma análise de currículo profissional e detalhada."},
                {"role": "user", "content": prompt_detalhado}
            ],
            temperature=0.5
        )
        resumo_ia = response.choices[0].message.content
    except Exception as e:
        resumo_ia = "Falha ao gerar resumo da IA. Analisando com o código..."

    pontuacao = 0
    habilidades_encontradas = []
    
    for habilidade, valor in Habilidades_Chave.items():
        if re.search(r'\b' + re.escape(habilidade) + r'\b', texto_curriculo, re.I):
            pontuacao += valor
            habilidades_encontradas.append(habilidade)
            
    certificacoes_encontradas = []
    for certificacao, valor in Certificacoes_Chave.items():
        if re.search(r'\b' + re.escape(certificacao) + r'\b', texto_curriculo, re.I):
            pontuacao += valor
            certificacoes_encontradas.append(certificacao)
    
    nome = texto_curriculo.split('\n')[0].strip() if '\n' in texto_curriculo else "Nome não encontrado"
    experiencia = re.findall(r'(\d+)\s+anos? de experiência', texto_curriculo, re.I)
    exp_anos = experiencia[0] if experiencia else "Não detectado"
    
    if pontuacao >= 70:
        status = "Pronto para Entrevista"
        justificativa = "A pontuação é alta devido às habilidades e certificações relevantes."
    elif pontuacao >= 40:
        status = "Analisar mais"
        justificativa = "O candidato tem habilidades, mas precisa de análise mais detalhada."
    else:
        status = "Não recomendado"
        justificativa = "O currículo não possui as habilidades-chave necessárias."
        
    return {
        "nome": nome,
        "resumo_analise": resumo_ia,
        "experiencia_anos": exp_anos,
        "habilidades_tecnicas": habilidades_encontradas,
        "certificacoes": certificacoes_encontradas,
        "pontuacao": min(pontuacao, 100),
