import typer
import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
import pdfplumber
from sentence_transformers import SentenceTransformer, util

app = typer.Typer()
PDF_DIR = ".\\data"
INDEX_DIR = 'index_storage'

import os
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env into environment

secret_token = os.getenv("OPENAI_API_KEY")
#print(secret_token)

@app.command()
def build_index(pdf_dir: str = PDF_DIR, index_dir: str = INDEX_DIR):
    documents = SimpleDirectoryReader(pdf_dir).load_data()
    index = VectorStoreIndex.from_documents(documents)
    index.storage_context.persist(persist_dir=index_dir)
    typer.echo(f"Index built and saved to {index_dir}")

@app.command()
def search(query: str, index_dir: str = INDEX_DIR):
    storage_context = StorageContext.from_defaults(persist_dir=index_dir)
    index = load_index_from_storage(storage_context)
    query_engine = index.as_query_engine()
    response = query_engine.query(query)
    typer.echo(response)


@app.command()
def summarise(pdf_dir: str = PDF_DIR):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    for filename in os.listdir(pdf_dir):
        if filename.lower().endswith('.pdf'):
            file_path = os.path.join(pdf_dir, filename)
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
            if text.strip():
                # Simple summarization: extract top 5 sentences by semantic similarity to the document embedding
                sentences = [s for s in text.split('\n') if len(s.split()) > 5]
                doc_embedding = model.encode([text], convert_to_tensor=True)
                sent_embeddings = model.encode(sentences, convert_to_tensor=True)
                cos_scores = util.pytorch_cos_sim(doc_embedding, sent_embeddings)[0]
                top_results = cos_scores.topk(5)
                abstract = "\n".join([sentences[idx] for idx in top_results[1]])
                typer.echo(f"Abstract for {filename}:\n{abstract}\n")
            else:
                typer.echo(f"No text found in {filename}")
if __name__ == "__main__":
    app()