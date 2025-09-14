import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.storage import Storage
from utils.helpers import format_time_remaining
from config import PREMIUM_PLANS, ADMIN_ID

storage = Storage()

async def show_upgrade_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show premium upgrade options"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Check current premium status
    is_premium = storage.get_user_property(user_id, 'is_premium')
    if is_premium:
        expiry = storage.get_bot_property(f"user_{user_id}_premium_expiry")
        plan = storage.get_bot_property(f"user_{user_id}_premium_plan")
        
        if expiry and int(expiry) > int(time.time() * 1000):
            expiry_date = time.strftime('%Y-%m-%d %H:%M', time.localtime(int(expiry) / 1000))
            await query.edit_message_text(
                f"🌟 You have an active *{plan}* premium plan.\n\n⏰ Expires on: *{expiry_date}*",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    
    # Show upgrade options
    buttons = [
        [InlineKeyboardButton("⭐ Weekly Plan", callback_data="select_weekly")],
        [InlineKeyboardButton("⭐ Monthly Plan", callback_data="select_monthly")],
        [InlineKeyboardButton("⭐ Yearly Plan", callback_data="select_yearly")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    message = """🎖 *Choose a Premium Plan*

Pick a subscription plan below to unlock premium features like:
✔️ Unlimited Likes
✔️ View Who Liked You  
✔️ See Matches
✔️ Boost Profile & More!

💳 After selecting a plan, you'll get the amount to send.
📸 Then upload your *payment screenshot* here to confirm."""
    
    await query.edit_message_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def select_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plan selection"""
    query = update.callback_query
    user_id = query.from_user.id
    plan_type = query.data.split('_')[1]  # weekly, monthly, yearly
    
    if plan_type not in PREMIUM_PLANS:
        await query.edit_message_text("❌ Invalid plan selected.")
        return
    
    plan = PREMIUM_PLANS[plan_type]
    
    # Save selected plan
    storage.set_user_property(user_id, 'selected_plan', plan_type)
    storage.set_user_property(user_id, 'awaiting_payment_proof', True)
    
    # Calculate expiry date
    import datetime
    expiry_date = datetime.datetime.now() + datetime.timedelta(days=plan['duration_days'])
    storage.set_user_property(user_id, 'premium_expiry_pending', expiry_date.isoformat())
    
    message = f"""💎 *{plan['name']} Selected*

Please send exactly *{plan['price']}* ({plan['price_usd']}).

📸 After payment, send your payment screenshot here so the admin can verify and activate your premium."""
    
    await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)

async def handle_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment proof upload"""
    user_id = update.effective_user.id
    
    awaiting_payment = storage.get_user_property(user_id, 'awaiting_payment_proof')
    if not awaiting_payment:
        return
    
    selected_plan = storage.get_user_property(user_id, 'selected_plan')
    if not selected_plan:
        await update.message.reply_text("❌ No plan selected. Please select a plan first.")
        return
    
    photo = update.message.photo[-1]
    
    # Save payment proof
    storage.set_user_property(user_id, 'payment_proof', photo.file_id)
    storage.set_user_property(user_id, 'awaiting_payment_proof', False)
    
    # Notify admin for verification
    plan_info = PREMIUM_PLANS[selected_plan]
    user_data = storage.get_user_data(user_id)
    user_name = user_data.get('name', 'Unknown')
    
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_payment_{user_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_payment_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_photo(
            ADMIN_ID,
            photo=photo.file_id,
            caption=f"💳 *Payment Verification Needed*\n\nUser: {user_name} (ID: {user_id})\nPlan: {plan_info['name']}\nAmount: {plan_info['price']} ({plan_info['price_usd']})",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except:
        pass
    
    await update.message.reply_text(
        "✅ Payment proof received! Your payment is being verified by our admin. You'll be notified once approved."
    )

async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin approves payment"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    if admin_id != ADMIN_ID:
        await query.answer("❌ Unauthorized", show_alert=True)
        return
    
    user_id = int(query.data.split('_')[2])
    selected_plan = storage.get_user_property(user_id, 'selected_plan')
    expiry_pending = storage.get_user_property(user_id, 'premium_expiry_pending')
    
    if not selected_plan or not expiry_pending:
        await query.edit_message_text("❌ Payment data not found.")
        return
    
    # Activate premium
    import datetime
    expiry_timestamp = int(datetime.datetime.fromisoformat(expiry_pending).timestamp() * 1000)
    
    storage.set_user_property(user_id, 'is_premium', True)
    storage.set_user_property(user_id, 'premium_plan', selected_plan)
    storage.set_bot_property(f"user_{user_id}_premium_expiry", expiry_timestamp)
    storage.set_bot_property(f"user_{user_id}_premium_plan", selected_plan)
    
    # Clean up
    storage.set_user_property(user_id, 'selected_plan', None)
    storage.set_user_property(user_id, 'premium_expiry_pending', None)
    storage.set_user_property(user_id, 'payment_proof', None)
    
    await query.edit_message_text("✅ Payment approved and premium activated!")
    
    # Notify user
    plan_info = PREMIUM_PLANS[selected_plan]
    try:
        await context.bot.send_message(
            user_id,
            f"🎉 *Premium Activated!*\n\nYour {plan_info['name']} is now active!\n\nEnjoy unlimited access to all premium features! 🌟",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass

async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin rejects payment"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    if admin_id != ADMIN_ID:
        await query.answer("❌ Unauthorized", show_alert=True)
        return
    
    user_id = int(query.data.split('_')[2])
    
    # Clean up
    storage.set_user_property(user_id, 'selected_plan', None)
    storage.set_user_property(user_id, 'premium_expiry_pending', None)
    storage.set_user_property(user_id, 'payment_proof', None)
    storage.set_user_property(user_id, 'awaiting_payment_proof', False)
    
    await query.edit_message_text("❌ Payment rejected.")
    
    # Notify user
    try:
        await context.bot.send_message(
            user_id,
            "❌ Your payment could not be verified. Please try again or contact support."
        )
    except:
        pass

async def boost_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Boost user's profile"""
    query = update.callback_query
    user_id = query.from_user.id
    
    is_premium = storage.get_user_property(user_id, 'is_premium')
    if not is_premium:
        await query.edit_message_text(
            "🚫 Only *premium users* can boost their profile.\n\nUpgrade your plan to use this feature.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    now = int(time.time() * 1000)
    last_boost = storage.get_user_property(user_id, 'last_boost_time') or 0
    boost_expiry = storage.get_user_property(user_id, 'boost_expires_at') or 0
    
    # Check if already boosted
    if boost_expiry > now:
        expiry_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(boost_expiry / 1000))
        await query.edit_message_text(
            f"✅ Your profile is already boosted until:\n*{expiry_str}*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Check cooldown (48 hours)
    cooldown_time = 48 * 60 * 60 * 1000  # 48 hours in milliseconds
    if last_boost and (now - last_boost) < cooldown_time:
        next_boost_time = last_boost + cooldown_time
        next_boost_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(next_boost_time / 1000))
        await query.edit_message_text(
            f"⏳ You can boost again on:\n*{next_boost_str}*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Apply boost
    boost_duration = 12 * 60 * 60 * 1000  # 12 hours in milliseconds
    storage.set_user_property(user_id, 'last_boost_time', now)
    storage.set_user_property(user_id, 'boost_expires_at', now + boost_duration)
    
    # Add to boosted profiles list
    boosted_profiles = storage.get_bot_property('boosted_profiles') or []
    if user_id not in boosted_profiles:
        boosted_profiles.append(user_id)
        storage.set_bot_property('boosted_profiles', boosted_profiles)
    
    await query.edit_message_text(
        "🚀 Your profile is boosted and will appear more in matches for the next *12 hours*!",
        parse_mode=ParseMode.MARKDOWN
    )
