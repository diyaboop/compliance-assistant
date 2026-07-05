from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_chroma import Chroma

def build_vectorstore(pdf_path="docs/eu_ai_act.pdf"):
    # 1. load PDF
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    # 2. split into chunks — size=500, overlap=50
    splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
    )
    chunks = splitter.split_documents(documents)
    # 3. create embedding function — all-MiniLM-L6-v2
    embedding_fn = SentenceTransformerEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )
    # 4. create and return Chroma vectorstore
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_fn,
        collection_name="eu_ai_act_langchain"
    )
    # 5. print confirmation with chunk count
    print(f"Documents stored:{vectorstore._collection.count()}")
    return vectorstore