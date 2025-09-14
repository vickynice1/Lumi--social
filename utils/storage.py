import json
import os
from typing import Any, Dict, List, Optional

class Storage:
    """Simple file-based storage system"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize files
        self.bot_data_file = os.path.join(data_dir, "bot_data.json")
        self.users_dir = os.path.join(data_dir, "users")
        os.makedirs(self.users_dir, exist_ok=True)
        
        # Load bot data
        self.bot_data = self._load_json(self.bot_data_file) or {}
    
    def _load_json(self, filepath: str) -> Optional[Dict]:
        """Load JSON from file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
        return None
    
    def _save_json(self, filepath: str, data: Dict):
        """Save JSON to file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving {filepath}: {e}")
    
    def get_user_data(self, user_id: int) -> Dict:
        """Get all user data"""
        user_file = os.path.join(self.users_dir, f"{user_id}.json")
        return self._load_json(user_file) or {}
    
    def save_user_data(self, user_id: int, data: Dict):
        """Save all user data"""
        user_file = os.path.join(self.users_dir, f"{user_id}.json")
        self._save_json(user_file, data)
    
    def get_user_property(self, user_id: int, key: str) -> Any:
        """Get specific user property"""
        user_data = self.get_user_data(user_id)
        return user_data.get(key)
    
    def set_user_property(self, user_id: int, key: str, value: Any):
        """Set specific user property"""
        user_data = self.get_user_data(user_id)
        user_data[key] = value
        self.save_user_data(user_id, user_data)
    
    def get_bot_property(self, key: str) -> Any:
        """Get bot-wide property"""
        return self.bot_data.get(key)
    
    def set_bot_property(self, key: str, value: Any):
        """Set bot-wide property"""
        self.bot_data[key] = value
        self._save_json(self.bot_data_file, self.bot_data)
    
    def get_all_users(self) -> List[Dict]:
        """Get all registered users"""
        users = []
        for filename in os.listdir(self.users_dir):
            if filename.endswith('.json'):
                user_id = int(filename[:-5])  # Remove .json
                user_data = self.get_user_data(user_id)
                if user_data.get('is_registered'):
                    user_data['user_id'] = user_id
                    users.append(user_data)
        return users
    
    def get_profiles(self) -> List[Dict]:
        """Get all complete profiles"""
        profiles = []
        for user_data in self.get_all_users():
            if user_data.get('profile_photo') and user_data.get('gender'):
                profiles.append({
                    'id': user_data['user_id'],
                    'name': user_data.get('name', 'Anonymous'),
                    'age': user_data.get('age'),
                    'gender': user_data.get('gender'),
                    'interest': user_data.get('interest'),
                    'location': user_data.get('location', 'Not specified'),
                    'bio': user_data.get('bio', 'No bio yet'),
                    'photo': user_data.get('profile_photo'),
                    'username': user_data.get('username')
                })
        return profiles
