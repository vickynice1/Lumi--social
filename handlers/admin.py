from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.storage import Storage
from config import ADMIN_ID

storage = Storage()

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 View Users", callback_data="admin_users")],
        [InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban")],
        [InlineKeyboardButton("✅ Unban User", callback_data="admin_unban")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🚨 Reports", callback_data="admin_reports")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔧 *Admin Panel*\n\nSelect an option:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    
    # Get statistics
    all_users = storage.get_all_users()
    total_users = len(all_users)
    
    premium_users = len([u for u in all_users if u.get('is_premium')])
    male_users = len([u for u in all_users if u.get('gender') == 'Male'])
    female_users = len([u for u in all_users if u.get('gender') == 'Female'])
    
    banned_users = storage.get_bot_property('banned_users') or []
    total_banned = len(banned_users)
    
    reports = storage.get_bot_property('user_reports') or []
    pending_reports = len(reports)
    
    message = f"""📊 *Bot Statistics*

👥 Total Users: *{total_users}*
🌟 Premium Users: *{premium_users}*
🚫 Banned Users: *{total_banned}*

👨 Male Users: *{male_users}*
👩 Female Users: *{female_users}*

🚨 Pending Reports: *{pending_reports}*"""
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def view_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View registered users"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    
    users = storage.get_all_users()
    
    if not users:
        await update.message.reply_text("❌ No users found.")
        return
    
    message = "👤 *Registered Users (First 30):*\n\n"
    
    for i, user_data in enumerate(users[:30]):
        name = user_data.get('name', 'No name')
        gender = user_data.get('gender', 'Unknown')
        age = user_data.get('age', 'N/A')
        user_id_display = user_data.get('user_id', 'Unknown')
        premium = "⭐" if user_data.get('is_premium') else ""
        
        message += f"{i+1}. {name} ({gender}, Age {age}) [ID: {user_id_display}] {premium}\n"
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    
    try:
        banned_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return
    
    # Add to banned list
    banned_users = storage.get_bot_property('banned_users') or []
    if banned_id not in banned_users:
        banned_users.append(banned_id)
        storage.set_bot_property('banned_users', banned_users)
    
    # Notify the banned user
    try:
        await context.bot.send_message(
            banned_id,
            "⛔ You have been banned by the admin. You can no longer use this bot."
        )
    except:
        pass
    
    await update.message.reply_text(f"✅ User {banned_id} has been banned.")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    
    try:
        unbanned_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return
    
    # Remove from banned list
    banned_users = storage.get_bot_property('banned_users') or []
    if unbanned_id in banned_users:
        banned_users.remove(unbanned_id)
        storage.set_bot_property('banned_users', banned_users)
        
        # Notify the unbanned user
        try:
            await context.bot.send_message(
                unbanned_id,
                "✅ You have been unbanned! You can now use the bot again."
            )
        except:
            pass
        
        await update.message.reply_text(f"✅ User {unbanned_id} has been unbanned.")
    else:
        await update.message.reply_text(f"❌ User {unbanned_id} is not banned.")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = ' '.join(context.args)
    users = storage.get_all_users()
    banned_users = storage.get_bot_property('banned_users') or []
    
    sent_count = 0
    failed_count = 0
    
    await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
    
    for user_data in users:
        target_id = user_data.get('user_id')
        if target_id and target_id not in banned_users:
            try:
                await context.bot.send_message(
                    target_id,
                    f"📢 *Admin Broadcast:*\n\n{message}",
                    parse_mode=ParseMode.MARKDOWN
                )
                sent_count += 1
            except:
                failed_count += 1
    
    await update.message.reply_text(
        f"✅ Broadcast complete!\n\n📤 Sent: {sent_count}\n❌ Failed: {failed_count}"
    )

async def view_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View user reports"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized.")
        return
    
    reports = storage.get_bot_property('user_reports') or []
    
    if not reports:
        await update.message.reply_text("✅ No pending reports.")
        return
    
    # Show first report
    report = reports[0]
    reporter_id = report['reporter_id']
    reported_id = report['reported_id']
    reason = report.get('reason', 'No reason provided')
    timestamp = report.get('timestamp', 0)
    
    import time
    report_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(timestamp))
    
    # Get user data
    reporter_data = storage.get_user_data(reporter_id)
    reported_data = storage.get_user_data(reported_id)
    
    reporter_name = reporter_data.get('name', 'Unknown')
    reported_name = reported_data.get('name', 'Unknown')
    
    keyboard = [
        [InlineKeyboardButton("⚠️ Warn User", callback_data=f"warn_user_{reported_id}")],
        [InlineKeyboardButton("🚫 Ban User", callback_data=f"ban_user_{reported_id}")],
        [InlineKeyboardButton("✅ Dismiss", callback_data=f"dismiss_report")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"""🚨 *User Report*

👤 Reporter: {reporter_name} (ID: {reporter_id})
🎯 Reported: {reported_name} (ID: {reported_id})
📝 Reason: {reason}
⏰ Time: {report_time}

Remaining reports: {len(reports)}"""
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warn a reported user"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    if admin_id != ADMIN_ID:
        await query.answer("❌ Unauthorized", show_alert=True)
        return
    
    warned_id = int(query.data.split('_')[2])
    
    # Add to warned users
    warned_users = storage.get_bot_property('warned_users') or []
    if warned_id not in warned_users:
        warned_users.append(warned_id)
        storage.set_bot_property('warned_users', warned_users)
    
    # Notify user
    try:
        await context.bot.send_message(
            warned_id,
            "⚠️ You have been warned by the admin. Repeated violations will lead to a ban. Please follow the rules."
        )
    except:
        pass
    
    # Remove report
    reports = storage.get_bot_property('user_reports') or []
    if reports:
        reports.pop(0)
        storage.set_bot_property('user_reports', reports)
    
    await query.edit_message_text(f"✅ User {warned_id} has been warned.")
    
    # Show next report if available
    if reports:
        await view_reports(update, context)

async def dismiss_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dismiss a report"""
    query = update.callback_query
    admin_id = query.from_user.id
    
    if admin_id != ADMIN_ID:
        await query.answer("❌ Unauthorized", show_alert=True)
        return
    
    # Remove report
    reports = storage.get_bot_property('user_reports') or []
    if reports:
        reports.pop(0)
        storage.set_bot_property('user_reports', reports)
    
    await query.edit_message_text("✅ Report dismissed.")
    
    # Show next report if available
    if reports:
        await view_reports(update, context)
