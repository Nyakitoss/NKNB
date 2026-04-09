import asyncio
import aiohttp
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from pathlib import Path

class NewsParser:
    def __init__(self):
        # Источники новостей (обновлено с расширенным списком)
        self.news_sources = [
            # Искусственный интеллект
            {
                "name": "OpenAI News",
                "url": "https://openai.com/news/rss.xml",
                "type": "rss",
                "category": "ai"
            },
            {
                "name": "DeepMind Blog",
                "url": "https://deepmind.google/discover/blog/rss.xml",
                "type": "rss",
                "category": "ai"
            },
            {
                "name": "VentureBeat AI",
                "url": "https://venturebeat.com/ai/rss.xml",
                "type": "rss",
                "category": "ai"
            },
            {
                "name": "MarkTechPost",
                "url": "https://www.marktechpost.com/feed/",
                "type": "rss",
                "category": "ai"
            },
            {
                "name": "Towards Data Science",
                "url": "https://towardsdatascience.com/feed",
                "type": "rss",
                "category": "ai"
            },
            {
                "name": "The Decoder",
                "url": "https://the-decoder.com/feed",
                "type": "rss",
                "category": "ai"
            },
            {
                "name": "AI Google Blog",
                "url": "https://ai.googleblog.com/rss.xml",
                "type": "rss",
                "category": "ai"
            },
            {
                "name": "Artificial Intelligence News",
                "url": "https://www.artificialintelligence-news.com/feed",
                "type": "rss",
                "category": "ai"
            },
            {
                "name": "Habr AI",
                "url": "https://habr.com/ru/hub/artificial_intelligence/rss",
                "type": "rss",
                "category": "ai"
            },
            {
                "name": "VC.ru AI",
                "url": "https://vc.ru/ai/rss",
                "type": "rss",
                "category": "ai"
            },
            {
                "name": "n+1 AI",
                "url": "https://nplus1.ru/ai/rss",
                "type": "rss",
                "category": "ai"
            },
            
            # Технологии
            {
                "name": "TechCrunch",
                "url": "https://techcrunch.com/feed/",
                "type": "rss",
                "category": "tech"
            },
            {
                "name": "The Verge",
                "url": "https://www.theverge.com/rss/index.xml",
                "type": "rss",
                "category": "tech"
            },
            {
                "name": "Ars Technica",
                "url": "https://arstechnica.com/rss",
                "type": "rss",
                "category": "tech"
            },
            {
                "name": "Wired",
                "url": "https://www.wired.com/feed/rss",
                "type": "rss",
                "category": "tech"
            },
            {
                "name": "Engadget",
                "url": "https://www.engadget.com/rss.xml",
                "type": "rss",
                "category": "tech"
            },
            {
                "name": "ZDNet",
                "url": "https://www.zdnet.com/news/rss.xml",
                "type": "rss",
                "category": "tech"
            },
            {
                "name": "CNET",
                "url": "https://www.cnet.com/rss/news/",
                "type": "rss",
                "category": "tech"
            },
            {
                "name": "Habr Tech",
                "url": "https://habr.com/ru/flows/news/rss",
                "type": "rss",
                "category": "tech"
            },
            {
                "name": "3DNews",
                "url": "https://3dnews.ru/rss",
                "type": "rss",
                "category": "tech"
            },
            {
                "name": "IXBT",
                "url": "https://ixbt.com/rss",
                "type": "rss",
                "category": "tech"
            },
            
            # Игры
            {
                "name": "IGN",
                "url": "https://www.ign.com/rss/news.xml",
                "type": "rss",
                "category": "games"
            },
            {
                "name": "GameSpot",
                "url": "https://www.gamespot.com/feeds/mashup/",
                "type": "rss",
                "category": "games"
            },
            {
                "name": "Kotaku",
                "url": "https://kotaku.com/rss",
                "type": "rss",
                "category": "games"
            },
            {
                "name": "PC Gamer",
                "url": "https://www.pcgamer.com/rss",
                "type": "rss",
                "category": "games"
            },
            {
                "name": "Rock Paper Shotgun",
                "url": "https://www.rockpapershotgun.com/feeds/news/",
                "type": "rss",
                "category": "games"
            },
            {
                "name": "StopGame",
                "url": "https://stopgame.ru/rss",
                "type": "rss",
                "category": "games"
            },
            {
                "name": "DTF Games",
                "url": "https://dtf.ru/games/rss",
                "type": "rss",
                "category": "games"
            },
            {
                "name": "GameGuru",
                "url": "https://gameguru.ru/rss",
                "type": "rss",
                "category": "games"
            },
            {
                "name": "GamesIndustry",
                "url": "https://gamesindustry.biz/rss",
                "type": "rss",
                "category": "games"
            },
            {
                "name": "Nintendolife",
                "url": "https://nintendolife.com/rss",
                "type": "rss",
                "category": "games"
            },
            
            # Наука
            {
                "name": "Science Daily",
                "url": "https://www.sciencedaily.com/rss/",
                "type": "rss",
                "category": "science"
            },
            {
                "name": "Nature News",
                "url": "https://www.nature.com/news/rss",
                "type": "rss",
                "category": "science"
            },
            {
                "name": "Science News",
                "url": "https://www.sciencenews.org/rss",
                "type": "rss",
                "category": "science"
            },
            {
                "name": "Live Science",
                "url": "https://www.livescience.com/rss",
                "type": "rss",
                "category": "science"
            },
            {
                "name": "Phys.org",
                "url": "https://phys.org/rss-feed.rss",
                "type": "rss",
                "category": "science"
            },
            {
                "name": "n+1 Наука",
                "url": "https://nplus1.ru/science/rss",
                "type": "rss",
                "category": "science"
            },
            {
                "name": "Elementy.ru",
                "url": "https://elementy.ru/rss",
                "type": "rss",
                "category": "science"
            },
            {
                "name": "New Scientist",
                "url": "https://www.newscientist.com/subject/technology/feed",
                "type": "rss",
                "category": "science"
            },
            {
                "name": "EurekAlert",
                "url": "https://www.eurekalert.org/rss",
                "type": "rss",
                "category": "science"
            },
            {
                "name": "Scientific American",
                "url": "https://www.scientificamerican.com/rss",
                "type": "rss",
                "category": "science"
            },
            
            # Экономика
            {
                "name": "Bloomberg Business",
                "url": "https://www.bloomberg.com/business/rss.xml",
                "type": "rss",
                "category": "business"
            },
            {
                "name": "Reuters Business",
                "url": "https://www.reuters.com/business/rss",
                "type": "rss",
                "category": "business"
            },
            {
                "name": "Financial Times",
                "url": "https://www.ft.com/rss/business",
                "type": "rss",
                "category": "business"
            },
            {
                "name": "CNBC",
                "url": "https://www.cnbc.com/id/100003114/device/rss/rss.xml",
                "type": "rss",
                "category": "business"
            },
            {
                "name": "Wall Street Journal",
                "url": "https://www.wsj.com/xml/rss/3_7031.xml",
                "type": "rss",
                "category": "business"
            },
            {
                "name": "РБК Экономика",
                "url": "https://rssexport.rbc.ru/rbcnews/free/economics.rss",
                "type": "rss",
                "category": "business"
            },
            {
                "name": "Коммерсантъ",
                "url": "https://www.kommersant.ru/rss/business.xml",
                "type": "rss",
                "category": "business"
            },
            {
                "name": "VC.ru Money",
                "url": "https://vc.ru/money/rss",
                "type": "rss",
                "category": "business"
            },
            {
                "name": "The Economist",
                "url": "https://www.economist.com/rss",
                "type": "rss",
                "category": "business"
            },
            {
                "name": "Trading Economics",
                "url": "https://tradingeconomics.com/rss",
                "type": "rss",
                "category": "business"
            },
            
            # Криптовалюты
            {
                "name": "Cointelegraph",
                "url": "https://cointelegraph.com/rss",
                "type": "rss",
                "category": "crypto"
            },
            {
                "name": "CoinDesk",
                "url": "https://www.coindesk.com/arc/out/rss.xml",
                "type": "rss",
                "category": "crypto"
            },
            {
                "name": "Decrypt",
                "url": "https://decrypt.co/feed",
                "type": "rss",
                "category": "crypto"
            },
            {
                "name": "Bitcoin Magazine",
                "url": "https://bitcoinmagazine.com/feed",
                "type": "rss",
                "category": "crypto"
            },
            {
                "name": "CryptoSlate",
                "url": "https://cryptoslate.com/feed",
                "type": "rss",
                "category": "crypto"
            },
            {
                "name": "Forklog",
                "url": "https://forklog.com/rss",
                "type": "rss",
                "category": "crypto"
            },
            {
                "name": "Bits Media",
                "url": "https://bits.media/rss",
                "type": "rss",
                "category": "crypto"
            },
            {
                "name": "CoinJournal",
                "url": "https://coinjournal.net/feed",
                "type": "rss",
                "category": "crypto"
            },
            {
                "name": "Cryptonews",
                "url": "https://cryptonews.com/rss",
                "type": "rss",
                "category": "crypto"
            },
            {
                "name": "News Bitcoin",
                "url": "https://news.bitcoin.com/feed",
                "type": "rss",
                "category": "crypto"
            },
            
            # Космос
            {
                "name": "Space.com",
                "url": "https://www.space.com/rss.xml",
                "type": "rss",
                "category": "space"
            },
            {
                "name": "SpaceNews",
                "url": "https://spacenews.com/rss",
                "type": "rss",
                "category": "space"
            },
            {
                "name": "NASA News",
                "url": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
                "type": "rss",
                "category": "space"
            },
            {
                "name": "ESA",
                "url": "https://www.esa.int/Science_Exploration/News_Events/rss",
                "type": "rss",
                "category": "space"
            },
            {
                "name": "Phys.org Space",
                "url": "https://phys.org/space-news/rss-feed.rss",
                "type": "rss",
                "category": "space"
            },
            {
                "name": "Universe Today",
                "url": "https://www.universetoday.com/rss",
                "type": "rss",
                "category": "space"
            },
            {
                "name": "n+1 Астрономия",
                "url": "https://nplus1.ru/astronomy/rss",
                "type": "rss",
                "category": "space"
            },
            {
                "name": "Astronomy.com",
                "url": "https://www.astronomy.com/rss",
                "type": "rss",
                "category": "space"
            },
            {
                "name": "Sky & Telescope",
                "url": "https://www.skyandtelescope.org/feed",
                "type": "rss",
                "category": "space"
            },
            
            # Медицина
            {
                "name": "Medical News Today",
                "url": "https://www.medicalnewstoday.com/rss/",
                "type": "rss",
                "category": "medicine"
            },
            {
                "name": "WebMD",
                "url": "https://www.webmd.com/rss/news",
                "type": "rss",
                "category": "medicine"
            },
            {
                "name": "NIH News",
                "url": "https://www.nih.gov/news-events/news.xml",
                "type": "rss",
                "category": "medicine"
            },
            {
                "name": "Science Daily Health",
                "url": "https://www.sciencedaily.com/health_medicine/rss",
                "type": "rss",
                "category": "medicine"
            },
            {
                "name": "Healthline",
                "url": "https://www.healthline.com/rss/news",
                "type": "rss",
                "category": "medicine"
            },
            {
                "name": "Meduza",
                "url": "https://meduza.io/rss",
                "type": "rss",
                "category": "medicine"
            },
            {
                "name": "MedPortal",
                "url": "https://medportal.ru/rss",
                "type": "rss",
                "category": "medicine"
            },
            {
                "name": "The Lancet",
                "url": "https://www.thelancet.com/rss",
                "type": "rss",
                "category": "medicine"
            },
            {
                "name": "JAMA Network",
                "url": "https://jamanetwork.com/rss",
                "type": "rss",
                "category": "medicine"
            },
            
            # Автомобили
            {
                "name": "Motor1.com",
                "url": "https://www.motor1.com/rss",
                "type": "rss",
                "category": "automotive"
            },
            {
                "name": "Autoblog",
                "url": "https://www.autoblog.com/rss",
                "type": "rss",
                "category": "automotive"
            },
            {
                "name": "Car and Driver",
                "url": "https://www.caranddriver.com/rss/auto-news.xml",
                "type": "rss",
                "category": "automotive"
            },
            {
                "name": "TopGear",
                "url": "https://www.topgear.com/car/rss",
                "type": "rss",
                "category": "automotive"
            },
            {
                "name": "InsideEVs",
                "url": "https://www.insideevs.com/rss",
                "type": "rss",
                "category": "automotive"
            },
            {
                "name": "Autoreview",
                "url": "https://www.autoreview.ru/rss",
                "type": "rss",
                "category": "automotive"
            },
            {
                "name": "Drom.ru",
                "url": "https://drom.ru/rss",
                "type": "rss",
                "category": "automotive"
            },
            {
                "name": "Kolesa.kz",
                "url": "https://kolesa.kz/rss",
                "type": "rss",
                "category": "automotive"
            },
            {
                "name": "Motor.ru",
                "url": "https://motor.ru/rss",
                "type": "rss",
                "category": "automotive"
            },
            {
                "name": "Autocar",
                "url": "https://www.autocar.co.uk/rss",
                "type": "rss",
                "category": "automotive"
            },
            
            # Кибербезопасность
            {
                "name": "KrebsOnSecurity",
                "url": "https://krebsonsecurity.com/news/rss.xml",
                "type": "rss",
                "category": "cybersecurity"
            },
            {
                "name": "The Record",
                "url": "https://therecord.media/feed/",
                "type": "rss",
                "category": "cybersecurity"
            },
            {
                "name": "Threatpost",
                "url": "https://threatpost.com/feed",
                "type": "rss",
                "category": "cybersecurity"
            },
            {
                "name": "Dark Reading",
                "url": "https://www.darkreading.com/rss",
                "type": "rss",
                "category": "cybersecurity"
            },
            {
                "name": "SecurityWeek",
                "url": "https://www.securityweek.com/rss",
                "type": "rss",
                "category": "cybersecurity"
            },
            {
                "name": "Securelist",
                "url": "https://securelist.ru/rss",
                "type": "rss",
                "category": "cybersecurity"
            },
            {
                "name": "Habr Security",
                "url": "https://habr.com/ru/hub/infosecurity/rss",
                "type": "rss",
                "category": "cybersecurity"
            },
            {
                "name": "The Hacker News",
                "url": "https://thehackernews.com/rss",
                "type": "rss",
                "category": "cybersecurity"
            },
            {
                "name": "Cybersecurity News",
                "url": "https://cybersecuritynews.com/feed",
                "type": "rss",
                "category": "cybersecurity"
            },
            
            # Политика
            {
                "name": "Reuters World",
                "url": "https://www.reuters.com/world/rss",
                "type": "rss",
                "category": "politics"
            },
            {
                "name": "BBC News",
                "url": "https://www.bbc.com/news/rss.xml",
                "type": "rss",
                "category": "politics"
            },
            {
                "name": "Al Jazeera",
                "url": "https://www.aljazeera.com/rss",
                "type": "rss",
                "category": "politics"
            },
            {
                "name": "The Guardian",
                "url": "https://www.theguardian.com/world/rss",
                "type": "rss",
                "category": "politics"
            },
            {
                "name": "CNN Politics",
                "url": "https://www.cnn.com/rss/politics.xml",
                "type": "rss",
                "category": "politics"
            },
            {
                "name": "Meduza Политика",
                "url": "https://meduza.io/politics/rss",
                "type": "rss",
                "category": "politics"
            },
            {
                "name": "РБК Политика",
                "url": "https://rssexport.rbc.ru/rbcnews/free/politics.rss",
                "type": "rss",
                "category": "politics"
            },
            {
                "name": "TASS",
                "url": "https://tass.ru/rss/v2.xml",
                "type": "rss",
                "category": "politics"
            },
            {
                "name": "RIA Новости",
                "url": "https://rian.ru/export/rss2/archive/politics.xml",
                "type": "rss",
                "category": "politics"
            },
            
            # Общество
            {
                "name": "BBC Society",
                "url": "https://www.bbc.com/news/world/rss",
                "type": "rss",
                "category": "society"
            },
            {
                "name": "The Guardian Society",
                "url": "https://www.theguardian.com/society/rss",
                "type": "rss",
                "category": "society"
            },
            {
                "name": "Vox Society",
                "url": "https://www.vox.com/society/rss",
                "type": "rss",
                "category": "society"
            },
            {
                "name": "NY Times Society",
                "url": "https://www.nytimes.com/svc/collections/v1/docapi/rss/society.xml",
                "type": "rss",
                "category": "society"
            },
            {
                "name": "Meduza Общество",
                "url": "https://meduza.io/society/rss",
                "type": "rss",
                "category": "society"
            },
            {
                "name": "Lenta.ru",
                "url": "https://lenta.ru/rss",
                "type": "rss",
                "category": "society"
            },
            {
                "name": "Current Time TV",
                "url": "https://www.currenttime.tv/rss",
                "type": "rss",
                "category": "society"
            },
            {
                "name": "Takiedela",
                "url": "https://takiedela.ru/rss",
                "type": "rss",
                "category": "society"
            },
            {
                "name": "The Atlantic",
                "url": "https://www.theatlantic.com/society/rss",
                "type": "rss",
                "category": "society"
            },
            {
                "name": "Euronews",
                "url": "https://www.euronews.com/rss",
                "type": "rss",
                "category": "society"
            },
            
            # Общие российские источники
            {
                "name": "РБК",
                "url": "https://rssexport.rbc.ru/rbcnews/free/rbc.ru_news.rss",
                "type": "rss",
                "category": "general"
            },
            {
                "name": "Коммерсантъ",
                "url": "https://www.kommersant.ru/rss/news.xml",
                "type": "rss", 
                "category": "general"
            },
            {
                "name": "Ведомости",
                "url": "https://www.vedomosti.ru/rss/rubric/all.xml",
                "type": "rss",
                "category": "general"
            },
            {
                "name": "TJournal",
                "url": "https://tjournal.ru/rss/all",
                "type": "rss",
                "category": "general"
            },
            {
                "name": "CNews",
                "url": "https://www.cnews.ru/inc/rss/news.xml",
                "type": "rss",
                "category": "general"
            },
            {
                "name": "РИА Новости",
                "url": "https://rian.ru/export/rss2/archive.xml",
                "type": "rss",
                "category": "general"
            },
            {
                "name": "Lenta.ru",
                "url": "https://lenta.ru/rss",
                "type": "rss",
                "category": "general"
            }
        ]
        
        self.cache_file = Path("/app/data/news_cache.json")
        self.cache_file.parent.mkdir(exist_ok=True)
        
        print(f"**LOG: News parser initialized with {len(self.news_sources)} sources**")
        print(f"**LOG: Sources by category:**")
        categories = {}
        for source in self.news_sources:
            cat = source["category"]
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
        
        for cat, count in categories.items():
            print(f"**LOG:   {cat}: {count} sources**")
        
    async def parse_all_sources(self) -> List[Dict]:
        """Парсит новости из всех источников"""
        all_news = []
        
        for source in self.news_sources:
            try:
                print(f"**LOG: Parsing news from {source['name']}**")
                news_items = await self._parse_source(source)
                all_news.extend(news_items)
                print(f"**LOG: Parsed {len(news_items)} items from {source['name']}**")
            except Exception as e:
                print(f"**LOG: Failed to parse {source['name']}: {str(e)}**")
                continue
                
        print(f"**LOG: Total news items parsed: {len(all_news)}**")
        return all_news
    
    async def _parse_source(self, source: Dict) -> List[Dict]:
        """Парсит один источник"""
        if source["type"] == "rss":
            return await self._parse_rss(source["url"])
        else:
            return []
    
    async def _parse_rss(self, url: str) -> List[Dict]:
        """Парсит RSS ленту"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        content = await response.text()
                        return self._parse_xml_content(content)
                    else:
                        print(f"**LOG: RSS fetch error: HTTP {response.status}**")
                        return []
        except Exception as e:
            print(f"**LOG: RSS parsing error: {str(e)}**")
            return []
    
    def _parse_xml_content(self, content: str) -> List[Dict]:
        """Парсит XML контент RSS"""
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(content)
            news_items = []
            
            # RSS каналы могут иметь разную структуру
            items = root.findall(".//item")
            
            for item in items:
                try:
                    title_elem = item.find("title")
                    desc_elem = item.find("description")
                    link_elem = item.find("link")
                    date_elem = item.find("pubDate")
                    
                    if title_elem is not None and desc_elem is not None:
                        title = title_elem.text or ""
                        description = desc_elem.text or ""
                        link = link_elem.text if link_elem is not None else ""
                        pub_date = date_elem.text if date_elem is not None else ""
                        
                        # Очищаем HTML теги из описания
                        import re
                        description = re.sub(r'<[^>]+>', '', description)
                        description = description.strip()
                        
                        # Проверяем, что новость не старше 24 часов
                        if self._is_recent_news(pub_date):
                            news_items.append({
                                "title": title.strip(),
                                "description": description[:500],  # Ограничиваем описание
                                "link": link,
                                "pub_date": pub_date,
                                "source": "RSS Feed"
                            })
                except Exception as e:
                    print(f"**LOG: Error parsing RSS item: {str(e)}**")
                    continue
                    
            return news_items[:50]  # Ограничиваем количество новостей
            
        except Exception as e:
            print(f"**LOG: XML parsing error: {str(e)}**")
            return []
    
    def _is_recent_news(self, pub_date: str) -> bool:
        """Strict check that news is not older than 24 hours with proper timezone handling"""
        try:
            if not pub_date:
                # If no date, assume it's recent but log warning
                print("**LOG: Warning - News item has no date, assuming recent**")
                return True
                
            current_time = datetime.now()
            
            # Parse date with multiple formats including timezone handling
            date_formats = [
                "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822 with timezone
                "%a, %d %b %Y %H:%M:%S %Z",  # RFC 2822 with UTC/GMT
                "%Y-%m-%dT%H:%M:%S%z",          # ISO 8601 with timezone
                "%Y-%m-%dT%H:%M:%SZ",          # ISO 8601 UTC
                "%a, %d %b %Y %H:%M:%S GMT",  # GMT format
                "%Y-%m-%d %H:%M:%S",           # Simple format
                "%Y-%m-%d",                    # Date only (assume midnight)
            ]
            
            parsed_date = None
            original_timezone = None
            
            for fmt in date_formats:
                try:
                    if "%z" in fmt or "%Z" in fmt:
                        # For timezone-aware formats
                        parsed_date = datetime.strptime(pub_date, fmt)
                        if parsed_date.tzinfo is not None:
                            original_timezone = parsed_date.tzinfo
                            # Convert to UTC first, then to local time
                            utc_time = parsed_date.astimezone(timezone.utc)
                            parsed_date = utc_time.replace(tzinfo=None)
                        else:
                            parsed_date = parsed_date.replace(tzinfo=None)
                    else:
                        # For naive formats
                        parsed_date = datetime.strptime(pub_date, fmt)
                        parsed_date = parsed_date.replace(tzinfo=None)
                    break
                except ValueError:
                    continue
            
            if parsed_date is None:
                print(f"**LOG: Warning - Could not parse date: {pub_date}**")
                return True  # If we can't parse, assume recent
            
            # Calculate time difference
            time_diff = current_time - parsed_date
            
            # Handle negative time differences (future dates)
            if time_diff.total_seconds() < 0:
                # News appears to be from the future, treat as recent
                hours_future = abs(time_diff.total_seconds()) / 3600
                print(f"**LOG: Future date detected: {hours_future:.1f} hours ahead, treating as recent**")
                return True
            
            # Strict 24-hour limit (86400 seconds)
            if time_diff.total_seconds() > 86400:
                print(f"**LOG: News too old: {time_diff.total_seconds()/3600:.1f} hours ago**")
                return False
            
            # Log age for debugging
            hours_ago = time_diff.total_seconds() / 3600
            print(f"**LOG: News age: {hours_ago:.1f} hours ago**")
            
            return True
            
        except Exception as e:
            print(f"**LOG: Date parsing error: {str(e)}**")
            return True  # If error, assume recent
    
    def get_cached_news(self) -> Optional[List[Dict]]:
        """Получает кэшированные новости"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    cache_time = datetime.fromisoformat(cache_data.get("timestamp", "2024-01-01"))
                    
                    # Проверяем, что кэш не старше 1 часа
                    if datetime.now() - cache_time < timedelta(hours=1):
                        print(f"**LOG: Using cached news from {cache_time}**")
                        return cache_data.get("news", [])
        except Exception as e:
            print(f"**LOG: Cache read error: {str(e)}**")
            
        return None
    
    def cache_news(self, news: List[Dict]):
        """Кэширует новости"""
        try:
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "news": news[:100]  # Ограничиваем кэш
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
            print(f"**LOG: Cached {len(news)} news items**")
            
        except Exception as e:
            print(f"**LOG: Cache write error: {str(e)}**")
    
    def filter_news_by_topics(self, news: List[Dict], topics: List[str]) -> List[Dict]:
        """Фильтрует новости по темам"""
        filtered_news = []
        topics_lower = [topic.lower() for topic in topics]
        
        for news_item in news:
            title_lower = news_item.get("title", "").lower()
            desc_lower = news_item.get("description", "").lower()
            
            # Проверяем вхождение тем в заголовок или описание
            for topic in topics_lower:
                if topic in title_lower or topic in desc_lower:
                    filtered_news.append(news_item)
                    break
                    
        print(f"**LOG: Filtered {len(filtered_news)} news items by topics: {', '.join(topics)}**")
        return filtered_news

# Глобальный экземпляр парсера
news_parser = NewsParser()
