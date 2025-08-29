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
        "justificativa_pontuacao": justificativa,
        "status_recomendacao": status,
    }

if menu == "🏠 Home":
    st.title("Fala, Micheline, tudo bem?")
    placeholder = st.empty()
    texto = "Sou seu Analista Virtual"
    displayed = ""
    for letra in texto:
        displayed += letra
        placeholder.write(f"_{displayed}_")
        time.sleep(0.1)

elif menu == "🏷️ Upload Currículos":
    st.title("📤 Upload de Currículos")
    st.markdown("Envie **PDF, DOCX ou TXT**. Use nomes de arquivo claros para facilitar a análise.")
    arquivos = st.file_uploader(
        "Selecione ou solte os arquivos aqui:",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )
    if arquivos:
        st.session_state["arquivos"] = arquivos
        st.success(f"✅ {len(arquivos)} arquivo(s) carregado(s) com sucesso!")
        
        # Processa e adiciona novos arquivos ao DataFrame existente
        novos_dados = []
        arquivos_carregados_nomes = [f.name for f in st.session_state.get("df_analise", pd.DataFrame())["Nome"].tolist()]
        
        for arquivo in arquivos:
            if arquivo.name not in arquivos_carregados_nomes:
                texto = ""
                if arquivo.type == "application/pdf":
                    reader = PdfReader(arquivo)
                    for page in reader.pages:
                        texto += page.extract_text() + "\n"
                elif arquivo.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    doc = Document(arquivo)
                    for para in doc.paragraphs:
                        texto += para.text + "\n"
                elif arquivo.type == "text/plain":
                    texto = arquivo.read().decode("utf-8")
                
                analise_ia = analisar_curriculo(texto)
                
                resumo_tecnico = f"""
                ✨ **Análise do Candidato**
                
                - **Nome:** {analise_ia.get("nome", "Talento Excellence")}
                - **Resumo IA:** {analise_ia.get("resumo_analise", "Resumo indisponível")}
                - **Experiência:** {analise_ia.get("experiencia_anos", "Não informado")} anos
                - **Pontuação:** {analise_ia.get("pontuacao", 0)}/100
                - **Justificativa:** {analise_ia.get("justificativa_pontuacao", "N/A")}
                - **Habilidades:** {", ".join(analise_ia.get("habilidades_tecnicas", [])) or 'Nenhuma detectada'}
                - **Certificações:** {", ".join(analise_ia.get("certificacoes", [])) or 'Nenhuma detectada'}
                
                ✅ **Status:** {analise_ia.get("status_recomendacao", "Revisão Manual")}
                """
                
                novos_dados.append({
                    "Nome": arquivo.name,
                    "Pontuação": analise_ia.get("pontuacao", 0),
                    "Status": analise_ia.get("status_recomendacao", "Revisão Manual"),
                    "Análise Completa": texto,
                    "ResumoIA": resumo_tecnico,
                    "Data de Upload": date.today()
                })
        
        if novos_dados:
            df_novos = pd.DataFrame(novos_dados)
            st.session_state["df_analise"] = pd.concat([st.session_state["df_analise"], df_novos], ignore_index=True)
            salvar_dados_analisados(st.session_state["df_analise"])
            salvar_curriculos(arquivos)


elif menu == "🚀 Analisador Excellence Big Tech":
    st.title("🚀 Analisador Virtual — Excellence Big Tech")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtros de Análise")
    
    df = st.session_state.get("df_analise", pd.DataFrame())
    
    if df.empty:
        st.warning("⚠️ Nenhum currículo encontrado. Faça o upload na seção 'Upload Currículos'.")
    else:
        status_filtro = st.sidebar.selectbox(
            "Filtrar por Status",
            ["Todos"] + list(df["Status"].unique())
        )
        
        hoje = date.today()
        data_filtro = st.sidebar.date_input("Filtrar por Data de Upload", value=hoje)
        
        df_filtrado = df.copy()

        if status_filtro != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Status"] == status_filtro]
        
        df_filtrado['Data de Upload'] = pd.to_datetime(df_filtrado['Data de Upload']).dt.date
        df_filtrado = df_filtrado[df_filtrado['Data de Upload'] == data_filtro]

        st.markdown("---")
        st.markdown("## 📋 Resultados da Análise")
        if not df_filtrado.empty:
            for idx, row in df_filtrado.iterrows():
                col1, col2 = st.columns([0.85, 0.15])
                
                with col1:
                    with st.expander(f"📄 {row['Nome']} - Status: {row['Status']}"):
                        st.markdown(row['ResumoIA'], unsafe_allow_html=True)
                        st.write("---")
                        st.markdown("### Conteúdo Completo do Currículo")
                        st.write(row['Análise Completa'])
                
                with col2:
                    if st.button("🗑️ Excluir", key=f"excluir_{row['Nome']}"):
                        df_temp = st.session_state["df_analise"]
                        st.session_state["df_analise"] = df_temp[df_temp["Nome"] != row["Nome"]]
                        salvar_dados_analisados(st.session_state["df_analise"])
                        st.experimental_rerun()
        else:
            st.warning("Nenhum currículo encontrado com os filtros aplicados.")

elif menu == "📅 RHday":
    st.title("📅 RHday — Agenda da Recrutadora")
    data = st.date_input("📅 Data")
    hora = st.time_input("⏰ Horário")
    nota = st.text_area("📝 Anotação da reunião/entrevista:")

    if st.button("💾 Salvar Evento"):
        if "agenda" not in st.session_state:
            st.session_state["agenda"] = []
        st.session_state["agenda"].append({
            "data": str(data),
            "hora": str(hora),
            "nota": nota
        })
        st.success(f"Evento salvo para {data} às {hora}.")

    if "agenda" in st.session_state and st.session_state["agenda"]:
        st.markdown("### 📌 Eventos Agendados:")
        for item in st.session_state["agenda"]:
            st.info(f"📅 {item['data']} ⏰ {item['hora']} — {item['nota']}")