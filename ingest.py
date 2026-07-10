import chromadb
from chromadb.utils import embedding_functions
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_data")

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(
    name="eu_ai_act",
    embedding_function=embedding_functions.DefaultEmbeddingFunction()
)

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

    # 3. add chunks to the module-level persistent collection
    #    (no local chroma_client/collection creation — use the ones defined above)
    collection.add(
        documents=[chunk.page_content for chunk in chunks],
        ids=[f"chunk_{i}" for i in range(len(chunks))]
    )

    # 4. print confirmation with chunk count
    print(f"Documents stored: {collection.count()}")
    return collection

def get_vectorstore():
    """Returns the existing collection without re-ingesting. Use this everywhere
    except the one-time setup script."""
    return collection