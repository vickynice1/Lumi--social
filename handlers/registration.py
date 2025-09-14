from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.storage import Storage
from utils.helpers import get_user_name

storage = Storage()

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the registration process"""
    user = update.effective_user
    user_id = user.id
    name = get_user_name(user)
    
    # Save basic user info
    storage.set_user_property(user_id, 'telegram_id', user_id)
    storage.set_user_property(user_id, 'username', user.username)
    storage.set_user_property(user_id, 'registration_state', 'awaiting_name')
    
    await update.message.reply_text(f"👋 Welcome, {name}!\n\nLet's set up your dating profile.\n\n👤 What name should we call you?")

async def handle_registration_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle registration input based on current state"""
    user_id = update.effective_user.id
    message_text = update.message.text
    state = storage.get_user_property(user_id, 'registration_state')
    
    if state == 'awaiting_name':
        await handle_name_input(update, context, message_text)
    elif state == 'awaiting_age':
        await handle_age_input(update, context, message_text)
    elif state == 'awaiting_location':
        await handle_location_input(update, context, message_text)
    elif state == 'awaiting_bio':
        await handle_bio_input(update, context, message_text)

async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE, name: str):
    """Handle name input"""
    user_id = update.effective_user.id
    
    if len(name) < 2 or len(name) > 50:
        await update.message.reply_text("❌ Please enter a valid name (2-50 characters).")
        return
    
    storage.set_user_property(user_id, 'name', name)
    storage.set_user_property(user_id, 'registration_state', 'awaiting_gender')
    
    keyboard = [
        [InlineKeyboardButton("Male", callback_data="gender_male")],
        [InlineKeyboardButton("Female", callback_data="gender_female")],
        [InlineKeyboardButton("Other", callback_data="gender_other")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ Nice to meet you, {name}!\n\n🚻 What's your gender?",
        reply_markup=reply_markup
    )

async def handle_gender_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle gender selection"""
    query = update.callback_query
    user_id = query.from_user.id
    gender = query.data.split('_')[1].capitalize()
    
    storage.set_user_property(user_id, 'gender', gender)
    storage.set_user_property(user_id, 'registration_state', 'awaiting_interest')
    
    keyboard = [
        [InlineKeyboardButton("Male", callback_data="interest_male")],
        [InlineKeyboardButton("Female", callback_data="interest_female")],
        [InlineKeyboardButton("Both", callback_data="interest_both")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ Gender set to {gender}!\n\n❤️ Who are you interested in?",
        reply_markup=reply_markup
    )

async def handle_interest_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interest selection"""
    query = update.callback_query
    user_id = query.from_user.id
    interest = query.data.split('_')[1].capitalize()
    
    storage.set_user_property(user_id, 'interest', interest)
    storage.set_user_property(user_id, 'registration_state', 'awaiting_age')
    
    await query.edit_message_text(f"✅ Interest set to {interest}!\n\n🎂 How old are you? (Enter a number between 18-100)")

async def handle_age_input(update: Update, context: ContextTypes.DEFAULT_TYPE, age_text: str):
    """Handle age input"""
    user_id = update.effective_user.id
    
    try:
        age = int(age_text)
        if age < 18 or age > 100:
            await update.message.reply_text("❌ Please enter a valid age between 18 and 100.")
            return
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number for your age.")
        return
    
    storage.set_user_property(user_id, 'age', age)
    storage.set_user_property(user_id, 'registration_state', 'awaiting_location')
    
    await update.message.reply_text("✅ Age saved!\n\n📍 Where are you located? (City, Country)")

async def handle_location_input(update: Update, context: ContextTypes.DEFAULT_TYPE, location: str):
    """Handle location input"""
    user_id = update.effective_user.id
    
    if len(location) < 2 or len(location) > 100:
        await update.message.reply_text("❌ Please enter a valid location (2-100 characters).")
        return
    
    storage.set_user_property(user_id, 'location', location)
    storage.set_user_property(user_id, 'registration_state', 'awaiting_bio')
    
    await update.message.reply_text("✅ Location saved!\n\n📝 Write a short bio about yourself (max 500 characters):")

async def handle_bio_input(update: Update, context: ContextTypes.DEFAULT_TYPE, bio: str):
    """Handle bio input"""
    user_id = update.effective_user.id
    
    if len(bio) > 500:
        await update.message.reply_text("❌ Bio is too long. Please keep it under 500 characters.")
        return
    
    storage.set_user_property(user_id, 'bio', bio)
    storage.set_user_property(user_id, 'registration_state', 'awaiting_photo')
    
    await update.message.reply_text("✅ Bio saved!\n\n📸 Now send a profile photo:")

async def handle_profile_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle profile photo upload"""
    user_id = update.effective_user.id
    photo = update.message.photo[-1]  # Get highest resolution
    
    # Save photo file_id
    storage.set_user_property(user_id, 'profile_photo', photo.file_id)
    storage.set_user_property(user_id, 'is_registered', True)
    storage.set_user_property(user_id, 'registration_state', None)
    
    await update.message.reply_text("✅ Profile photo saved and registration complete! 🎉")
    
    # Show main menu
    from bot import start
    await start(update, context)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's profile"""
    query = update.callback_query
    user_id = query.from_user.id
    
    user_data = storage.get_user_data(user_id)
    if not user_data or not user_data.get('is_registered'):
        await query.edit_message_text("❌ Profile not found. Please register first.")
        return
    
    # Check premium status
    is_premium = user_data.get('is_premium', False)
    premium_tag = "❌ Not Premium"
    
    if is_premium:
        plan = user_data.get('premium_plan', '').lower()
        if plan == 'weekly':
            premium_tag = "💫 Premium (Weekly)"
        elif plan == 'monthly':
            premium_tag = "💎 Premium (Monthly)"
        elif plan == 'yearly':
            premium_tag = "👑 Premium (Yearly)"
        else:
            premium_tag = "⭐ Premium"
    
    # Build profile message
    caption = f"""👤 *Your Profile Preview*

🧑 Name: *{user_data.get('name', 'Anonymous')}* {premium_tag}
🚻 Gender: *{user_data.get('gender', 'Unknown')}*
🎂 Age: *{user_data.get('age', 'N/A')}*
📍 Location: *{user_data.get('location', 'Not set')}*
📝 Bio: _{user_data.get('bio', 'No bio yet')}_
🆔 Username: @{user_data.get('username', 'N/A')}"""
    
    # Send profile photo with caption
    photo_id = user_data.get('profile_photo')
    if photo_id:
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=photo_id,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await query.edit_message_text(caption, parse_mode=ParseMode.MARKDOWN)
