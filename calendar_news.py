import datetime
import holidays
import feedparser

def get_market_status(selected_date=None):
    """இன்றைய அல்லது தேர்ந்தெடுக்கப்பட்ட நாளில் மார்க்கெட் திறந்திருக்குமா எனச் சரிபார்க்கும்."""
    if selected_date is None:
        selected_date = datetime.date.today()

    weekday = selected_date.weekday()
    in_holidays = holidays.India(years=selected_date.year)

    # 1. சனி & ஞாயிறு செக்
    if weekday == 5:
        return False, "🔴 Market Closed (Saturday - வார இறுதி விடுமுறை)"
    if weekday == 6:
        return False, "🔴 Market Closed (Sunday - வார இறுதி விடுமுறை)"

    # 2. இந்திய அரசு / பண்டிகை விடுமுறை செக்
    if selected_date in in_holidays:
        holiday_name = in_holidays.get(selected_date)
        return False, f"🟠 Market Holiday ({holiday_name} - டிரேடிங் இல்லை)"

    return True, "🟢 Market Open (டிரேடிங் நடக்கும் நாள்)"


def get_high_impact_news():
    """மார்க்கெட்டைப் பாதிக்கும் முக்கிய செய்திகளை RSS மூலம் ஆட்டோமேட்டிக்காக எடுக்கும்."""
    rss_urls = [
        "https://news.google.com/rss/search?q=NIFTY+OR+RBI+OR+Fed+Rate+OR+Inflation+stock+market+India&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Gold+XAUUSD+OR+US+CPI+OR+FOMC+market+impact&hl=en-IN&gl=IN&ceid=IN:en"
    ]
    high_impact_keywords = [
        "rbi", "fed", "rate", "cpi", "inflation", "gdp", "budget",
        "fomc", "nfp", "crash", "rally", "tariff", "war", "nifty", "gold"
    ]

    news_items = []
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:6]:
                title = entry.get("title", "")
                link = entry.get("link", "#")
                published = entry.get("published", "")
                is_high = any(k in title.lower() for k in high_impact_keywords)
                news_items.append({
                    "title": title,
                    "link": link,
                    "published": published[:16],
                    "impact": "🔴 HIGH" if is_high else "🟡 MEDIUM"
                })
        except Exception:
            continue

    # டூப்ளிகேட் நீக்கி முதல் 8 செய்திகளை மட்டும் காட்டு
    seen = set()
    unique_news = []
    for item in news_items:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique_news.append(item)
        if len(unique_news) >= 8:
            break

    return unique_news
  
