from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.storage import Storage
from utils.helpers import contains_banned_words, add_notification
from config import ADMIN_ID

storage = Storage()

async def show_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's active chats"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Get matches (potential chats)
    matches = storage.get_bot_property(f"matches_{user_id}") or []
    
    if not matches:
        await query.edit_message_text("💬 No chats available. Get some matches first!")
        return
    
    # Build chat list
    message = "💬 *Your Chats:*\n\nSelect someone to start chatting:\n\n"
    buttons = []
    
    for match_id in matches[:10]:  # Show first 10
        match_data = storage.get_user_data(match_id)
        if match_data:
            name = match_data.get('name', 'Anonymous')
            buttons.append([InlineKeyboardButton(f"💬 {name}", callback_data=f"start_chat_{match_id}")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await query.edit_message_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def start_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a chat with a matched user"""
    query = update.callback_query
    user_id = query.from_user.id
    partner_id = int(query.data.split('_')[2])
    
    # Verify they are matched
    matches = storage.get_bot_property(f"matches_{user_id}") or []
    if partner_id not in matches:
        await query.edit_message_text("❌ You can only chat with your matches.")
        return
    
    # Set chat session
    storage.set_bot_property(f"chat_{user_id}", partner_id)
    storage.set_bot_property(f"chat_{partner_id}", user_id)
    
    partner_data = storage.get_user_data(partner_id)
    partner_name = partner_data.get('name', 'Anonymous')
    user_data = storage.get_user_data(user_id)
    user_name = user_data.get('name', 'Anonymous')
    
    # Notify both users
    keyboard = [
        [InlineKeyboardButton("🚫 Report User", callback_data=f"report_{partner_id}")],
        [InlineKeyboardButton("❌ End Chat", callback_data="end_chat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💬 *Chat started with {partner_name}!*\n\nYou can now send messages, photos, and more. Be respectful!\n\n🔒 This is an anonymous chat.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    # Notify partner
    try:
        await context.bot.send_message(
            partner_id,
            f"💬 *{user_name} started a chat with you!*\n\nYou can now send messages. Be respectful!\n\n🔒 This is an anonymous chat.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except:
        pass  # Partner might have blocked the bot

async def handle_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in active chat"""
    user_id = update.effective_user.id
    partner_id = storage.get_bot_property(f"chat_{user_id}")
    
    if not partner_id:
        return
    
    message_text = update.message.text
    
    # Check for banned words
    if contains_banned_words(message_text):
        # Ban user and end chat
        banned_users = storage.get_bot_property('banned_users') or []
        if user_id not in banned_users:
            banned_users.append(user_id)
            storage.set_bot_property('banned_users', banned_users)
        
        # End chat for both users
        storage.set_bot_property(f"chat_{user_id}", None)
        storage.set_bot_property(f"chat_{partner_id}", None)
        
        await update.message.reply_text("🚫 You have been banned for offensive language.")
        
        try:
            await context.bot.send_message(
                partner_id,
                "⚠️ Chat ended due to offensive content from the other user."
            )
        except:
            pass
        
        # Notify admin
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"🚨 User {user_id} auto-banned for offensive message: \"{message_text}\""
            )
        except:
            pass
        
        return
    
    # Forward message with reply button
    keyboard = [[InlineKeyboardButton("💬 Reply", callback_data=f"reply_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            partner_id,
            f"💌 *Anonymous message:*\n\n{message_text}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except:
        await update.message.reply_text("❌ Failed to send message. The user might have blocked the bot.")

async def handle_chat_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos in active chat"""
    user_id = update.effective_user.id
    partner_id = storage.get_bot_property(f"chat_{user_id}")
    
    if not partner_id:
        return
    
    photo = update.message.photo[-1]
    caption = update.message.caption or ""
    
    # Forward photo with reply button
    keyboard = [[InlineKeyboardButton("💬 Reply", callback_data=f"reply_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_photo(
            partner_id,
            photo=photo.file_id,
            caption=f"📸 *Anonymous photo:*\n\n{caption}" if caption else "📸 *Anonymous photo*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except:
        await update.message.reply_text("❌ Failed to send photo. The user might have blocked the bot.")

async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End active chat"""
    query = update.callback_query
    user_id = query.from_user.id
    partner_id = storage.get_bot_property(f"chat_{user_id}")
    
    if not partner_id:
        await query.edit_message_text("❌ No active chat to end.")
        return
    
    # End chat for both users
    storage.set_bot_property(f"chat_{user_id}", None)
    storage.set_bot_property(f"chat_{partner_id}", None)
    
    await query.edit_message_text("✅ Chat ended.")
    
    # Notify partner
    try:
        await context.bot.send_message(partner_id, "💔 The other user ended the chat.")
    except:
        pass

async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Report a user"""
    query = update.callback_query
    user_id = query.from_user.id
    reported_id = int(query.data.split('_')[1])
    
    # Save report
    reports = storage.get_bot_property('user_reports') or []
    report = {
        'reporter_id': user_id,
        'reported_id': reported_id,
        'timestamp': int(time.time()),
        'reason': 'General misconduct'
    }
    reports.append(report)
    storage.set_bot_property('user_reports', reports)
    
    # End chat
    storage.set_bot_property(f"chat_{user_id}", None)
    storage.set_bot_property(f"chat_{reported_id}", None)
    
    await query.edit_message_text("✅ User reported. Chat ended. Thank you for keeping our community safe.")
    
    # Notify admin
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"🚨 New report:\nReporter: {user_id}\nReported: {reported_id}\nReason: General misconduct"
        )
    except:
        pass
