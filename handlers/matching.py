import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.storage import Storage
from utils.helpers import get_current_week, filter_profiles_by_interest, shuffle_list, add_notification

storage = Storage()

async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Find and show a potential match"""
    if update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        chat_id = query.message.chat_id
    else:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
    
    user_data = storage.get_user_data(user_id)
    
    # Check if user is registered
    if not user_data.get('is_registered'):
        await context.bot.send_message(chat_id, "❗ Please complete your profile first.")
        return
    
    my_gender = user_data.get('gender')
    my_interest = user_data.get('interest')
    is_premium = user_data.get('is_premium', False)
    
    # Check browse limits for free users
    if not is_premium:
        current_week = get_current_week()
        last_browse_week = user_data.get('last_browse_week', 0)
        browse_count = user_data.get('weekly_browse_count', 0)
        
        if current_week == last_browse_week and browse_count >= 10:
            keyboard = [[InlineKeyboardButton("🌟 Upgrade to Premium", callback_data="upgrade")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id,
                "🚫 You have used up your free allowance for this week.\n\n🌟 *Upgrade to Premium* to get unlimited access.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        
        # Update browse count
        if current_week != last_browse_week:
            browse_count = 0
        browse_count += 1
        storage.set_user_property(user_id, 'weekly_browse_count', browse_count)
        storage.set_user_property(user_id, 'last_browse_week', current_week)
    
    # Get all profiles
    all_profiles = storage.get_profiles()
    
    if not all_profiles:
        await context.bot.send_message(chat_id, "⚠️ No profiles found. Please try again later.")
        return
    
    # Filter profiles based on interest
    candidates = filter_profiles_by_interest(all_profiles, my_gender, my_interest, user_id)
    
    if not candidates:
        await context.bot.send_message(chat_id, "😔 No available profiles right now. Try again later!")
        return
    
    # Get last shown profile to avoid repeats
    last_shown_id = user_data.get('last_shown_match', 0)
    
    # Shuffle and find next profile
    shuffled = shuffle_list(candidates)
    next_profile = None
    
    for profile in shuffled:
        if profile['id'] != last_shown_id:
            next_profile = profile
            break
    
    if not next_profile:
        next_profile = shuffled[0]  # Fallback to first profile
    
    # Update last shown
    storage.set_user_property(user_id, 'last_shown_match', next_profile['id'])
    
    # Build profile message
    name = next_profile['name']
    age = next_profile['age']
    gender = next_profile['gender']
    bio = next_profile['bio']
    location = next_profile['location']
    username = next_profile.get('username', '')
    
    caption = f"""💘 *Match Found!*
🧑 Name: *{name}*
🚻 Gender: *{gender}*
🎂 Age: *{age}*
📍 Location: *{location}*
📝 Bio: {bio}

🎉😍"""
    
    # Build buttons
    buttons = [
        [
            InlineKeyboardButton("❤️ Like", callback_data=f"like_{next_profile['id']}"),
            InlineKeyboardButton("❌ Pass", callback_data="find_match")
        ]
    ]
    
    if is_premium and username:
        buttons.append([InlineKeyboardButton("💬 Chat", url=f"https://t.me/{username}")])
    elif not is_premium:
        buttons.append([InlineKeyboardButton("🔒 Upgrade to Premium to Chat", callback_data="upgrade")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    # Send profile
    photo_id = next_profile.get('photo')
    if photo_id:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo_id,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id,
            caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

async def like_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user like action"""
    query = update.callback_query
    user_id = query.from_user.id
    liked_user_id = int(query.data.split('_')[1])
    
    # Get user data
    user_data = storage.get_user_data(user_id)
    user_name = user_data.get('name', 'Someone')
    
    # Add to liked users list
    liked_users = user_data.get('liked_users', [])
    if liked_user_id not in liked_users:
        liked_users.append(liked_user_id)
        storage.set_user_property(user_id, 'liked_users', liked_users)
    
    # Add to the other user's likes list
    other_user_likes = storage.get_bot_property(f"likes_{liked_user_id}") or []
    if user_id not in other_user_likes:
        other_user_likes.append(user_id)
        storage.set_bot_property(f"likes_{liked_user_id}", other_user_likes)
    
    # Check if it's a match (both users liked each other)
    other_user_data = storage.get_user_data(liked_user_id)
    other_user_liked = other_user_data.get('liked_users', [])
    
    if user_id in other_user_liked:
        # It's a match!
        await handle_match(user_id, liked_user_id, user_name, other_user_data.get('name', 'Someone'))
        
        await query.edit_message_text(
            "🎉 *IT'S A MATCH!* 💕\n\nYou both liked each other! Check your matches to start chatting.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Just a like
        add_notification(liked_user_id, f"❤️ {user_name} liked your profile!")
        
        await query.edit_message_text("❤️ Like sent! Looking for more matches...")
        
        # Show next match
        await find_match(update, context)

async def handle_match(user1_id: int, user2_id: int, user1_name: str, user2_name: str):
    """Handle when two users match"""
    import time
    
    # Add to matches for both users
    user1_matches = storage.get_bot_property(f"matches_{user1_id}") or []
    user2_matches = storage.get_bot_property(f"matches_{user2_id}") or []
    
    if user2_id not in user1_matches:
        user1_matches.append(user2_id)
        storage.set_bot_property(f"matches_{user1_id}", user1_matches)
    
    if user1_id not in user2_matches:
        user2_matches.append(user1_id)
        storage.set_bot_property(f"matches_{user2_id}", user2_matches)
    
    # Add notifications
    add_notification(user1_id, f"🎉 You matched with {user2_name}!")
    add_notification(user2_id, f"🎉 You matched with {user1_name}!")

async def view_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View user's matches"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Check if premium
    is_premium = storage.get_user_property(user_id, 'is_premium')
    if not is_premium:
        keyboard = [[InlineKeyboardButton("🌟 Upgrade to Premium", callback_data="upgrade")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔒 This feature is only available to *Premium* users.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # Get matches
    matches = storage.get_bot_property(f"matches_{user_id}") or []
    
    if not matches:
        await query.edit_message_text("💔 No matches yet. Keep browsing to find your perfect match!")
        return
    
    # Build matches message
    message = "💕 *Your Matches:*\n\n"
    buttons = []
    
    for i, match_id in enumerate(matches[:10]):  # Show first 10 matches
        match_data = storage.get_user_data(match_id)
        if match_data:
            name = match_data.get('name', 'Anonymous')
            age = match_data.get('age', '?')
            message += f"{i+1}. {name}, {age}\n"
            
            buttons.append([InlineKeyboardButton(f"💬 Chat with {name}", callback_data=f"start_chat_{match_id}")])
    
    # Mark matches as seen
    storage.set_bot_property(f"seen_matches_{user_id}", len(matches))
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await query.edit_message_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def view_likes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View who liked the user"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Check if premium
    is_premium = storage.get_user_property(user_id, 'is_premium')
    if not is_premium:
        keyboard = [[InlineKeyboardButton("🌟 Upgrade to Premium", callback_data="upgrade")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔒 This feature is only available to *Premium* users.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # Get likes
    likes = storage.get_bot_property(f"likes_{user_id}") or []
    
    if not likes:
        await query.edit_message_text("🙁 Nobody has liked your profile yet. Keep browsing and engaging to increase visibility!")
        return
    
    # Build likes message
    message = "👀 *People who liked your profile:*\n\n"
    
    for i, liker_id in enumerate(likes[:20]):  # Show first 20 likes
        liker_data = storage.get_user_data(liker_id)
        if liker_data:
            name = liker_data.get('name', 'Anonymous')
            gender = liker_data.get('gender', '?')
            age = liker_data.get('age', '?')
            message += f"{i+1}. {name} — 🧍 {gender}, 🎂 {age}\n"
    
    # Mark likes as seen
    storage.set_bot_property(f"seen_likes_{user_id}", len(likes))
    
    await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
