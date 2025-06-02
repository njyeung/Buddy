import os
from pprint import pprint
import re
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
from serpapi import GoogleSearch
from bs4 import BeautifulSoup
import requests

from uprint import OutGoingDataType, uprint
from tool_decorator import tool

# Load .env
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    dotenv_path = ".env"
    open(dotenv_path, "a").close()

def get_serpapi_key():
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        uprint("Enter your SerpAPI key: ", OutGoingDataType.PROMPT, "SERPAPI")

    return api_key

# Tools

@tool("Performs a web search and returns a list of results")
def web_search(query:str, num_results:int=10):
    api_key = get_serpapi_key()

    if not api_key:
        return "SERPAPI_API_KEY missing from .env file. A window has opened up in the frontend prompting the user for their credentials."
    
    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": num_results
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    organic = results.get("organic_results", [])[:num_results]
    
    organic_results = [
        {
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet"),
            "thumbnail": item.get("thumbnail"),
            "source": item.get("source")
        } for item in organic
    ]

    return organic_results

@tool("Fetches and extracts readable content from a live webpage URL (e.g., https://example.com). This is for retrieving online articles or web data.")
def web_fetch_page(url:str, max_chars:int=5000):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Request failed: {str(e)}"

    soup = BeautifulSoup(response.text, 'html.parser')

    # Remove non-content elements
    for tag in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav', 'aside', 'svg']):
        tag.decompose()

    # Extract meaningful content based on tag importance
    important_tags = ['header', 'a', 'button' 'h1', 'h2', 'h3', 'h4', 'span', 'p', 'ul', 'li', 'article', 'section']
    content = []

    for tag in soup.find_all(important_tags):
        text = tag.get_text(strip=True)
        if not text:
            continue

        # Skip junk patterns
        if re.search(r'\b(menu|close|copy link|embed|embedded|share|copyright|login|log in|subscribe|cookie|advertis|terms|privacy)\b', text, re.IGNORECASE):
            continue

        # For anchor tags, include href
        if tag.name == 'a' and tag.has_attr('href'):
            href = tag['href']
            content.append(f"{text} ({href})")
        else:
            content.append(text)

    combined = '\n'.join(content)

    return combined[:max_chars]