from os import read
import requests
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor


def get_urls():
 with open("text.txt","r") as f:
    urls = [url.strip() for url in f.readlines()]
    return urls





def scraper(url):
#for url in urls:
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    #response = requests.get(robots_url)
    rp = RobotFileParser()
    rp.set_url(robots_url)
    rp.read()
    allowed = rp.can_fetch("ME",url)
    if allowed:
        response = requests.get(url)
        soup = BeautifulSoup(response.text,"html.parser")
        text = soup.title
        return url,text 
         
    else:
      print("not allowed")
      return url,None
       
    
    
store = {}
with ThreadPoolExecutor(max_workers=10) as executor:
    result = executor.map(scraper,get_urls())
    for url,text in result:
        store[url]=text



print(store)