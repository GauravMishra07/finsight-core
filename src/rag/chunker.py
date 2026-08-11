# src/rag/chunker.py
from langchain_text_splitters import RecursiveCharacterTextSplitter
from bs4 import BeautifulSoup
from config.logger import setup_logger

logger = setup_logger(__name__)

class TextChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        # Using 1000 chars ensures chunks stay within all-MiniLM's token limit
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

    def clean_html(self, raw_html: str) -> str:
        """Strips HTML/XBRL tags and converts SEC filing into clean plain text."""
        logger.info("Cleaning HTML/XBRL markup from SEC document...")
        soup = BeautifulSoup(raw_html, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Extract plain text with clean line breaks
        text = soup.get_text(separator="\n")
        
        # Strip excessive blank lines
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        cleaned_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return cleaned_text

    def chunk_text(self, raw_text: str):
        # 1. Strip raw HTML markup
        cleaned_text = self.clean_html(raw_text)
        
        logger.info(f"Cleaned text size: {len(cleaned_text)} characters (reduced from {len(raw_text)})")
        
        # 2. Split cleaned text into vector-friendly chunks
        return self.splitter.split_text(cleaned_text)

chunker = TextChunker()