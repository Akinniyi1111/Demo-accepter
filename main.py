import json
import os
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ChatJoinRequestHandler,
    MessageHandler,
    filters,
)

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"welcome_msg": "Hello {name}, your request has been approved!", "users": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


data = load_data()

# ───────────────────────────────────────────
# 🔐 Load bot token and admin IDs
# ───────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = os.getenv("ADMIN_IDS", "")

ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS.split(",") if x.strip().isdigit()]

def is_admin(user_id):
    return user_id in ADMIN_IDS


# ───────────────────────────────────────────
# 🟦 Start
# ───────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("Access denied. You are not an admin.")
        return

    keyboard = [
        [InlineKeyboardButton("✏ Edit Welcome Msg", callback_data="edit_welcome")],
        [InlineKeyboardButton("♻ Reset Welcome Msg", callback_data="reset_welcome")],
        [InlineKeyboardButton("📢 Send Broadcast", callback_data="send_broadcast")],
        [InlineKeyboardButton("📺 Add to Channel", callback_data="add_channel")],
        [InlineKeyboardButton("👥 Add to Group", callback_data="add_group")],
    ]

    await update.message.reply_text(
        "Admin Panel:", reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ───────────────────────────────────────────
# 📌 Handle Inline Button Actions
# ───────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if not is_admin(user_id):
        await query.edit_message_text("You are not an admin.")
        return

    # Edit welcome message
    if query.data == "edit_welcome":
        context.user_data["editing_welcome"] = True
        await query.edit_message_text("Send the new welcome message now.\nUse {name} for username.")
        return

    # Reset welcome message
    if query.data == "reset_welcome":
        data["welcome_msg"] = "Hello {name}, your request has been approved!"
        save_data(data)
        await query.edit_message_text("Welcome message has been reset successfully.")
        return

    # Broadcast
    if query.data == "send_broadcast":
        context.user_data["broadcasting"] = True
        await query.edit_message_text("Send the broadcast message now.")
        return

    # Add to Channel (manual instructions)
    if query.data == "add_channel":
        await query.edit_message_text(
            "Telegram does NOT allow bots to automatically detect your channels.\n\n"
            "👉 Please manually add the bot as an ADMIN in the channel.\n"
            "✓ Enable: Invite Users\n"
            "✓ Enable: Approve Join Requests (if approval mode is ON)\n\n"
            "After adding, the bot will automatically start approving members."
        )
        return

    # Add to Group (manual)
    if query.data == "add_group":
        await query.edit_message_text(
            "Please manually add the bot to your GROUP and grant admin permissions:\n\n"
            "✓ Add Members\n"
            "✓ Approve Join Requests (if required)\n\n"
            "Once added, the bot will work automatically."
        )
        return


# ───────────────────────────────────────────
# ✏ Receive new welcome message
# ───────────────────────────────────────────
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text

    if is_admin(user_id):

        # Save new welcome message
        if context.user_data.get("editing_welcome"):
            data["welcome_msg"] = msg
            save_data(data)
            context.user_data["editing_welcome"] = False
            await update.message.reply_text("Welcome message updated successfully.")
            return

        # Broadcast message
        if context.user_data.get("broadcasting"):
            count = 0
            for uid in data["users"]:
                try:
                    await context.bot.send_message(uid, msg)
                    count += 1
                except:
                    pass

            await update.message.reply_text(f"Broadcast sent to {count} users.")
            context.user_data["broadcasting"] = False
            return


# ───────────────────────────────────────────
# 🔔 Auto Approve Join Requests
# ───────────────────────────────────────────
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    user = req.from_user
    name = user.first_name

    # Approve
    await req.approve()

    # Store user
    if user.id not in data["users"]:
        data["users"].append(user.id)
        save_data(data)

    # Send welcome message
    welcome_text = data["welcome_msg"].format(name=name)
    try:
        await context.bot.send_message(user.id, welcome_text)
    except:
        pass


# ───────────────────────────────────────────
# ▶ Run Bot
# ───────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))
    app.add_handler(ChatJoinRequestHandler(join_request))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
