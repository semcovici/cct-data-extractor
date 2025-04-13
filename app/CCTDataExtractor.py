import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_community.document_loaders import UnstructuredPDFLoader


# =============================================================================
# Modelos de Dados com Pydantic
# =============================================================================
class Seguro(BaseModel):
    nome_cobertura: str = Field(..., description="Nome da cobertura/seguro")
    limite: str = Field(..., description="Valor ou descrição do limite da cobertura")


class CCTData(BaseModel):
    cnpj: str = Field(..., description="CNPJ da empresa ou sindicato")
    nome: str = Field(..., description="Nome da empresa ou sindicato")
    inicio_vigencia: str = Field(..., description="Data de início de vigência do acordo")
    fim_vigencia: str = Field(..., description="Data de fim de vigência do acordo")
    seguro: list[Seguro] = Field(..., description="Lista de dados do seguro, contendo nome da cobertura e limite")


# =============================================================================
# Classe para Extração de Dados da CCT a partir de um PDF
# =============================================================================
class CCTDataExtractor:
    """
    Classe para extrair informações de arquivos PDF de Convenção Coletiva de Trabalho (CCT)
    utilizando um modelo da OpenAI por meio da cadeia de prompts do LangChain.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.0, max_completion_tokens=None):
        """
        Inicializa o extrator, definindo as configurações do LLM e ajustando variáveis de ambiente.

        Args:
            api_key (str): Chave de API da OpenAI.
            model (str): Modelo a ser utilizado.
            temperature (float): Parâmetro de temperatura para o modelo.
        """
        # Define a chave da API se ainda não estiver configurada
        if not os.environ.get("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = api_key

        self.llm = ChatOpenAI(model=model, temperature=temperature, max_completion_tokens=max_completion_tokens)

        # Configuração do parser para saída no formato JSON baseado no modelo CCTData
        self.output_parser = PydanticOutputParser(pydantic_object=CCTData)

        # Definição do template de prompt para extração de informações do PDF
        self.prompt_template = PromptTemplate(
            template=(
                "Você é um assistente especializado em analisar documentos de Convenção Coletiva de Trabalho (CCT) e extrair informações específicas.\n"
                "Extraia os seguintes dados do documento:\n\n"
                "Dados Básicos (normalmente nas 1ª ou 2ª páginas):\n"
                "- CNPJ\n"
                "- Nome\n"
                "- Início de Vigência\n"
                "- Fim de Vigência\n\n"
                "Dados do Seguro (geralmente apresentados em formato de grid em páginas intermediárias):\n"
                "- Nome da Cobertura (primeira coluna)\n"
                "- Limite (segunda coluna)\n\n"
                "Caso alguma informação não seja encontrada, retorne 'Não encontrado' para esse campo.\n\n"
                "Formate sua resposta no formato JSON conforme as instruções abaixo:\n"
                "{format_instructions}\n\n"
                "Documento:\n"
                "{pdf_text}\n"
            ),
            input_variables=["pdf_text"],
            partial_variables={"format_instructions": self.output_parser.get_format_instructions()}
        )

    def load_pdf(self, file_path: str) -> str:
        """
        Carrega e concatena o conteúdo textual extraído de um PDF.

        Args:
            file_path (str): Caminho para o arquivo PDF.

        Returns:
            str: O texto extraído do PDF.
        """
        loader = UnstructuredPDFLoader(
            file_path,
            coordinates=True,
            mode="elements",
            languages=["por"]
        )
        documents = loader.load()
        return "\n\n".join(doc.page_content for doc in documents)

    def create_chain(self):

        chain = self.prompt_template | self.llm | self.output_parser

        return chain

    def extract_data(self, pdf_text: str) -> CCTData:
        """
        Realiza a extração dos dados a partir do texto do PDF utilizando o LLM.

        Args:
            pdf_text (str): Conteúdo textual extraído do PDF.

        Returns:
            CCTData: Objeto com os dados extraídos.
        """

        chain = self.create_chain()

        return chain.invoke({"pdf_text":pdf_text})


    def extract_from_pdf(self, pdf_file: str) -> CCTData:
        """
        Realiza todas as etapas para extrair dados de um PDF, podendo salvar o texto processado.

        Args:
            pdf_file (str): Caminho para o arquivo PDF.
            save_processed (bool): Indica se o texto extraído deve ser salvo em um arquivo.
            processed_path (Optional[str]): Caminho onde o texto processado será salvo (se aplicável).

        Returns:
            CCTData: Dados extraídos do documento.
        """
        pdf_text = self.load_pdf(pdf_file)

        return self.extract_data(pdf_text)