import streamlit as st
import tempfile
import os
import json
import pandas as pd
import io

from CCTDataExtractor import CCTDataExtractor

# Configuração do OCR (se necessário)
os.environ["OCR_AGENT"] = "unstructured.partition.utils.ocr_models.tesseract_ocr.OCRAgentTesseract"

# Configuração da API Key via st.secrets (certifique-se que o arquivo .streamlit/secrets.toml existe)
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

# Título da aplicação
st.title("Extração de Dados de PDF - CCT")

st.write("Arraste o seu arquivo PDF e clique no botão para iniciar a extração das informações.")

# Área de upload do arquivo PDF
uploaded_pdf = st.file_uploader("Selecione um arquivo PDF", type=["pdf"])

if uploaded_pdf is not None:
    if st.button("Extrair Informações"):
        # Cria um arquivo temporário para salvar o PDF (necessário para que o extrator trabalhe com um caminho de arquivo)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_pdf.read())
            tmp_pdf_path = tmp_file.name

        try:
            # Inicializa a instância do extrator com a API Key
            extractor = CCTDataExtractor(api_key=os.environ["OPENAI_API_KEY"])
            # Executa a extração a partir do PDF
            cct_data = extractor.extract_from_pdf(tmp_pdf_path)

            # Converte o resultado para um dicionário (compatível com pydantic v2 ou v1)
            data = cct_data.model_dump() if hasattr(cct_data, "model_dump") else cct_data.dict()

            # Organiza os dados básicos em um DataFrame
            basic_data = pd.DataFrame([{
                'CNPJ': data.get('cnpj', ''),
                'Nome': data.get('nome', ''),
                'Início Vigência': data.get('inicio_vigencia', ''),
                'Fim Vigência': data.get('fim_vigencia', '')
            }])

            # Organiza a lista de seguros (caso exista) em um DataFrame
            seguros = data.get('seguro', [])
            seguros_df = pd.DataFrame(seguros) if isinstance(seguros, list) and seguros else pd.DataFrame()

            st.success("Extração realizada com sucesso!")

            # Exibe as tabelas na interface do Streamlit
            st.subheader("Dados Básicos")
            st.table(basic_data)

            if not seguros_df.empty:
                st.subheader("Seguros")
                st.table(seguros_df)

            # Cria um arquivo Excel em memória contendo as tabelas
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                basic_data.to_excel(writer, sheet_name='Dados Básicos', index=False)
                if not seguros_df.empty:
                    seguros_df.to_excel(writer, sheet_name='Seguros', index=False)
            output.seek(0)
            excel_data = output.getvalue()

            # Botão de download do Excel
            st.download_button(
                label="Baixar Excel",
                data=excel_data,
                file_name="dados_extraidos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Erro ao extrair dados: {e}")
        finally:
            # Remove o arquivo temporário após o processamento
            os.remove(tmp_pdf_path)