from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
import os
import sys
# Add parent dir to path to import logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import get_logger

logger = get_logger(__name__)

KNOWLEDGE_FILE = "data/kdi_knowledge.txt"
PERSIST_DIR = "data/chroma_db"

def ingest():
    if not os.path.exists(KNOWLEDGE_FILE):
        logger.error(f"Error: {KNOWLEDGE_FILE} not found.")
        return

    logger.info("Loading documents...")
    loader = TextLoader(KNOWLEDGE_FILE, encoding="utf-8")
    documents = loader.load()

    logger.info("Splitting text into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""],
        length_function=len
    )
    docs = text_splitter.split_documents(documents)
    logger.info(f"Split into {len(docs)} chunks.")

    logger.info("Initializing HuggingFace embeddings...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    logger.info(f"Creating ChromaDB and saving to {PERSIST_DIR}...")
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )
    vectorstore.persist()
    logger.info("Ingestion complete!")

if __name__ == "__main__":
    ingest()
