import chromadb
from chromadb.utils import embedding_functions
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

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

    # 3. create chromadb client + collection using the built-in default
    # embedding function — avoids loading a separate FastEmbed/ONNX model
    chroma_client = chromadb.Client()
    collection = chroma_client.create_collection(
        name="eu_ai_act",
        embedding_function=embedding_functions.DefaultEmbeddingFunction()
    )

    # 4. add chunks to the collection
    collection.add(
        documents=[chunk.page_content for chunk in chunks],
        ids=[f"chunk_{i}" for i in range(len(chunks))]
    )
    # 5. print confirmation with chunk count
    print(f"Documents stored: {collection.count()}")
    return collection
