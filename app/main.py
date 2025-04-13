import streamlit as st
import tempfile
import os
import json
import pandas as pd
import io

from CCTDataExtractor import CCTDataExtractor

# Configuração do OCR (se necessário)
os.environ["OCR_AGENT"] = "unstructured.partition.utils.ocr_models.tesseract_ocr.OCRAgentTesseract"

# Configuração da API Key via st.secrets (certifique-se de que o arquivo .streamlit/secrets.toml existe)
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

st.title("Extração de Dados de Múltiplos PDFs - CCT")
st.write("Arraste os seus arquivos PDF e clique no botão para iniciar a extração das informações.")

# Área de upload para múltiplos arquivos PDF
uploaded_pdfs = st.file_uploader("Selecione arquivos PDF", type=["pdf"], accept_multiple_files=True)

if uploaded_pdfs:
    if st.button("Extrair Informações"):
        total_files = len(uploaded_pdfs)
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Listas para acumular os registros dos dados básicos e dos seguros
        basic_records = []
        seguros_records = []

        # Inicializa a instância do extrator (utilizada para todos os arquivos)
        extractor = CCTDataExtractor(api_key=os.environ["OPENAI_API_KEY"])

        for i, pdf in enumerate(uploaded_pdfs):
            status_text.text(f"Processando o arquivo {i+1} de {total_files}: {pdf.name}")

            # Cria um arquivo temporário para cada PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(pdf.read())
                tmp_pdf_path = tmp_file.name

            try:
                cct_data = extractor.extract_from_pdf(tmp_pdf_path)
                data = cct_data.model_dump() if hasattr(cct_data, "model_dump") else cct_data.dict()

                # Registra os dados básicos com identificação do arquivo
                basic_records.append({
                    'Arquivo': pdf.name,
                    'CNPJ': data.get('cnpj', ''),
                    'Nome': data.get('nome', ''),
                    'Início Vigência': data.get('inicio_vigencia', ''),
                    'Fim Vigência': data.get('fim_vigencia', '')
                })

                # Registra os dados de seguros, se existentes, adicionando o nome do arquivo
                seguros = data.get('seguro', [])
                if isinstance(seguros, list) and seguros:
                    for seg in seguros:
                        seguros_records.append({
                            'Arquivo': pdf.name,
                            'Nome da Cobertura': seg.get('nome_cobertura', ''),
                            'Limite': seg.get('limite', '')
                        })
            except Exception as e:
                st.error(f"Erro ao processar o arquivo {pdf.name}: {e}")
            finally:
                os.remove(tmp_pdf_path)

            # Atualiza a barra de progresso
            progress_bar.progress((i + 1) / total_files)

        status_text.text("Processamento concluído!")

        # Cria DataFrames a partir dos registros coletados
        basic_df = pd.DataFrame(basic_records)
        seguros_df = pd.DataFrame(seguros_records)

        st.subheader("Dados Básicos")
        st.table(basic_df)
        if not seguros_df.empty:
            st.subheader("Seguros")
            st.table(seguros_df)

        # Cria um arquivo Excel em memória com duas abas
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            basic_df.to_excel(writer, sheet_name='Dados Básicos', index=False)
            if not seguros_df.empty:
                seguros_df.to_excel(writer, sheet_name='Seguros', index=False)
        output.seek(0)
        excel_data = output.getvalue()

        # Botão para download do arquivo Excel
        st.download_button(
            label="Baixar Excel",
            data=excel_data,
            file_name="dados_extraidos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
