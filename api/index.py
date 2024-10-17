from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import time
import logging

app = Flask(__name__)

class CustomFilter(logging.Filter):
    def filter(self, record):
        return "GET /?__debugger__=" not in record.getMessage()

logger = logging.getLogger('werkzeug')
logger.addFilter(CustomFilter())

# Set X-Frame-Options Header globally
@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    return response

def fetch_episode_links(season):
    url = f'https://egybest.land/series/%D9%85%D8%B3%D9%84%D8%B3%D9%84-from-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-{season}/'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
        "Accept-Encoding": "*",
        "Connection": "keep-alive",
        'Content-Type': 'application/json',
        'accept': 'application/json'
    }

    max_retries = 1000
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}. Attempt {attempt + 1}.")
            time.sleep(0.01)
    else:
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    episodes_div = soup.select_one('body > section > div > div:nth-of-type(2) > section > div:nth-of-type(3) > div')
    episodes = episodes_div.find_all('div') if episodes_div else []

    episode_links = []
    for episode in episodes:
        link_tag = episode.find('a')
        if link_tag:
            title = link_tag.get_text(strip=True)
            start = title.find("حلقة")
            if start != -1:
                title = title[start:]
                end = title.find(' ', 5)
                if end != -1:
                    title = title[:end]
                try:
                    number = int(title.replace("حلقة", "").strip())
                except ValueError:
                    number = float('inf')
                link = link_tag['href']
                episode_links.append({'title': title, 'link': link, 'number': number})

    episode_links.sort(key=lambda x: x['number'])
    for ep in episode_links:
        del ep['number']
    return episode_links

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_episodes')
def get_episodes():
    season = request.args.get('season', 'الاول')
    episodes = fetch_episode_links(season)
    return jsonify({'episode_links': episodes})

@app.route('/fetch_episode')
def fetch_episode():
    episode_link = request.args.get('episode_link')
    if episode_link:
        headers = {"User-Agent": "Mozilla/5.0"}
        max_retries = 1000
        for attempt in range(max_retries):
            try:
                response = requests.get(episode_link, headers=headers)
                if response.status_code == 200:
                    break
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error: {e}. Attempt {attempt + 1}.")
                time.sleep(0.01)
        else:
            return f"Error fetching episode page."

        soup = BeautifulSoup(response.content, 'html.parser')
        servers_div = soup.select_one('div.story.watchServer')
        server_links = []
        if servers_div:
            for server in servers_div.select('ul.serverWatch li'):
                name = server.get_text(strip=True)
                url = server.get('data-embed', '#')
                server_links.append({'name': name, 'url': url})
        return render_template('server_links.html', server_links=server_links)
    return "Episode link not found."

if __name__ == '__main__':
    app.run()
