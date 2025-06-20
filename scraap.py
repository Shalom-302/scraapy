
from tavily import TavilyClient
from dotenv import load_dotenv
import os
load_dotenv()
tavily_key= os.getenv("TAVILY_API_KEY")

tavily_client = TavilyClient(api_key=tavily_key)
response = tavily_client.search("Who is Leo Messi?")

print(response)