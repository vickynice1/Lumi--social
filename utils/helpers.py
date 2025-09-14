import time
import random
from typing import List, Dict
from telegram import User
from utils.storage import Storage

storage = Storage()

def get_user_name(user: User) -> str:
    """Get user's display name"""
    return user.first_name or user.username or "dear"

def is_banned(user_id: int) -> bool:
    """Check if user is banned"""
    banned_users = storage.get_bot_property('banned_users') or []
    return user_id in banned_users

def is_premium(user_id: int) -> bool:
    """Check if user has active premium"""
    return storage.get_user_property(user_id, 'is_premium') or False

def get_current_week() -> int:
    """Get current week number"""
    import datetime
    now = datetime.datetime.now()
    return now.isocalendar()[1]

def shuffle_list(lst: List) -> List:
    """Shuffle a list"""
    shuffled = lst.copy()
    random.shuffle(shuffled)
    return shuffled

def filter_profiles_by_interest(profiles: List[Dict], user_gender: str, user_interest: str, user_id: int) -> List[Dict]:
    """Filter profiles based on user's interest"""
    return [
        profile for profile in profiles
        if profile['id'] != user_id and profile['gender'] == user_interest
    ]

def format_time_remaining(timestamp: int) -> str:
    """Format time remaining from timestamp"""
    now = int(time.time() * 1000)
    if timestamp <= now:
        return "Expired"
    
    remaining = (timestamp - now) // 1000  # Convert to seconds
    
    if remaining < 3600:  # Less than 1 hour
        minutes = remaining // 60
        return f"{minutes} minutes"
    elif remaining < 86400:  # Less than 1 day
        hours = remaining // 3600
        return f"{hours} hours"
    else:  # Days
        days = remaining // 86400
        return f"{days} days"

def contains_banned_words(text: str) -> bool:
    """Check if text contains banned words"""
    from config import BANNED_WORDS
    text_lower = text.lower()
    return any(word in text_lower for word in BANNED_WORDS)

def add_notification(user_id: int, message: str):
    """Add notification for user"""
    notifications = storage.get_user_property(user_id, 'notifications') or []
    notifications.append({
        'message': message,
        'timestamp': int(time.time())
    })
    # Keep only last 50 notifications
    if len(notifications) > 50:
        notifications = notifications[-50:]
    storage.set_user_property(user_id, 'notifications', notifications)
