import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import asyncio

from config import BOT_TOKEN, ADMIN_ID
from handlers import registration, matching, premium, chat, admin
from utils.storage import Storage
from utils.helpers import is_banned, get_user_name

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize storage
storage = Storage()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    user_id = user.id
    
    # Check if user is banned
    if is_banned(user_id):
        await update.message.reply_text("⛔ You are banned from using this bot.")
        return
    
    name = get_user_name(user)
    
    # Check if user is registered
    user_data = storage.get_user_data(user_id)
    if user_data and user_data.get('is_registered'):
        # Update premium status
        await update_premium_status(user_id)
        
        # Get notifications count
        notifications = storage.get_user_property(user_id, 'notifications') or []
        notif_badge = f" ({len(notifications)})" if notifications else ""
        
        # Show main menu
        keyboard = [
            [InlineKeyboardButton("💘 Find Match", callback_data="find_match"),
             InlineKeyboardButton("👤 My Profile", callback_data="my_profile")],
            [InlineKeyboardButton("🚀 Upgrade", callback_data="upgrade"),
             InlineKeyboardButton("💬 My Chats", callback_data="my_chats")],
            [InlineKeyboardButton("🚀 Boost Profile", callback_data="boost_profile"),
             InlineKeyboardButton(f"🔔 Notifications{notif_badge}", callback_data="notifications")],
            [InlineKeyboardButton("⚠️ Reset Account", callback_data="reset_account")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"👋 Welcome back, {name}!\nWhat would you like to do today?",
            reply_markup=reply_markup
        )
    else:
        # Register new user
        await update.message.reply_text(f"👋 Welcome, {name}!\n\nLet's get you registered before matching begins.")
        await registration.start_registration(update, context)

async def update_premium_status(user_id: int):
    """Update user's premium status"""
    expiry = storage.get_bot_property(f"user_{user_id}_premium_expiry")
    plan = storage.get_bot_property(f"user_{user_id}_premium_plan")
    
    import time
    now = int(time.time() * 1000)
    
    if expiry and int(expiry) > now:
        # Still valid
        storage.set_user_property(user_id, 'is_premium', True)
        storage.set_user_property(user_id, 'premium_plan', plan)
    else:
        # Expired
        storage.set_user_property(user_id, 'is_premium', False)
        storage.set_user_property(user_id, 'premium_plan', None)
        storage.set_bot_property(f"user_{user_id}_premium_expiry", None)
        storage.set_bot_property(f"user_{user_id}_premium_plan", None)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard buttons"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # Check if user is banned
    if is_banned(user_id):
        await query.edit_message_text("⛔ You are banned from using this bot.")
        return
    
    # Route to appropriate handlers
    if data == "find_match":
        await matching.find_match(update, context)
    elif data == "my_profile":
        await registration.show_profile(update, context)
    elif data == "upgrade":
        await premium.show_upgrade_options(update, context)
    elif data == "my_chats":
        await chat.show_chats(update, context)
    elif data == "boost_profile":
        await premium.boost_profile(update, context)
    elif data == "notifications":
        await show_notifications(update, context)
    elif data.startswith("like_"):
        await matching.like_user(update, context)
    elif data.startswith("pass_"):
        await matching.find_match(update, context)
    elif data.startswith("select_"):
        await premium.select_plan(update, context)
    # Add more handlers as needed

async def show_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user notifications"""
    query = update.callback_query
    user_id = query.from_user.id
    
    is_premium = storage.get_user_property(user_id, 'is_premium') or False
    
    # Get notifications
    notices = storage.get_bot_property(f"notifies_{user_id}") or []
    likes = storage.get_bot_property(f"likes_{user_id}") or []
    matches = storage.get_bot_property(f"matches_{user_id}") or []
    
    seen_likes = storage.get_bot_property(f"seen_likes_{user_id}") or 0
    seen_matches = storage.get_bot_property(f"seen_matches_{user_id}") or 0
    
    new_likes = max(0, len(likes) - seen_likes)
    new_matches = max(0, len(matches) - seen_matches)
    
    if not notices:
        message = "🔕 You have no new notifications."
    else:
        message = "📬 *Your Notifications:*\n\n"
        for i, notice in enumerate(notices):
            message += f"{i + 1}. {notice}\n"
    
    # Build buttons
    buttons = []
    if is_premium:
        buttons.extend([
            [InlineKeyboardButton(f"🎉 View Matches ({new_matches})", callback_data="view_matches")],
            [InlineKeyboardButton(f"❤️ View Likes ({new_likes})", callback_data="view_likes")]
        ])
    else:
        buttons.extend([
            [InlineKeyboardButton(f"🎉 View Matches ({new_matches})", callback_data="upgrade")],
            [InlineKeyboardButton(f"❤️ View Likes ({new_likes})", callback_data="upgrade")]
        ])
    
    if notices:
        buttons.append([InlineKeyboardButton("🗑️ Clear Notifications", callback_data="clear_notifications")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await query.edit_message_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    
    # Check if user is banned
    if is_banned(user_id):
        await update.message.reply_text("⛔ You are banned from using this bot.")
        return
    
    # Check if user is in chat mode
    partner_id = storage.get_bot_property(f"chat_{user_id}")
    if partner_id:
        await chat.handle_chat_message(update, context)
        return
    
    # Check if user is in registration process
    user_state = storage.get_user_property(user_id, 'registration_state')
    if user_state:
        await registration.handle_registration_input(update, context)
        return
    
    # Default response
    await update.message.reply_text("Please use the menu buttons or type /start")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
    user_id = update.effective_user.id
    
    # Check if user is banned
    if is_banned(user_id):
        await update.message.reply_text("⛔ You are banned from using this bot.")
        return
    
    # Check if user is in chat mode
    partner_id = storage.get_bot_property(f"chat_{user_id}")
    if partner_id:
        await chat.handle_chat_photo(update, context)
        return
    
    # Check if user is uploading profile photo
    user_state = storage.get_user_property(user_id, 'registration_state')
    if user_state == 'awaiting_photo':
        await registration.handle_profile_photo(update, context)
        return
    
    # Check if user is uploading payment proof
    awaiting_payment = storage.get_user_property(user_id, 'awaiting_payment_proof')
    if awaiting_payment:
        await premium.handle_payment_proof(update, context)
        return

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    
    # Add admin handlers
    application.add_handler(CommandHandler("admin", admin.admin_panel))
    application.add_handler(CommandHandler("ban", admin.ban_user))
    application.add_handler(CommandHandler("unban", admin.unban_user))
    application.add_handler(CommandHandler("broadcast", admin.broadcast_message))
    application.add_handler(CommandHandler("stats", admin.show_stats))
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
