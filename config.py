import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '5727413041'))

# Premium plans pricing
PREMIUM_PLANS = {
    'weekly': {
        'name': 'Weekly Plan',
        'price': '1300 Stars',
        'duration_days': 7,
        'price_usd': '$31.96'
    },
    'monthly': {
        'name': 'Monthly Plan', 
        'price': '2600 Stars',
        'duration_days': 30,
        'price_usd': '$63.91'
    },
    'yearly': {
        'name': 'Yearly Plan',
        'price': '5200 Stars',
        'duration_days': 365,
        'price_usd': '$127.83'
    }
}

# Bot settings
FREE_WEEKLY_BROWSE_LIMIT = 10
BOOST_DURATION_HOURS = 12
BOOST_COOLDOWN_HOURS = 48

# Banned words for chat moderation
BANNED_WORDS = [
    'fuck', 'bitch', 'nude', 'sex', 'ass', 'dick', 'boobs', 
    'fag', 'slut', 'porn', 'xxx', 'horny', 'pussy'
]
