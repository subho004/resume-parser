import httpx
# from bs4 import BeautifulSoup
from markitdown import MarkItDown


async def extract_content(url:str):
        md = MarkItDown()
        result= md.convert(url)
        return result.text_content
