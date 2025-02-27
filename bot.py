from telegram import Update, Bot, ChatAction, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import requests

# Replace with your actual bot token and DeepSeek API key
TOKEN = '7960288096:AAEx7FuiZoQ0JJ4crM1j7D1ZMCcViJvgH3Y'
DEEPSEEK_API_KEY = 'sk-0ac92130ed544cc398633f098860dfc5'
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'

# Replace with your Discord webhook URL
DISCORD_WEBHOOK_URL = 'YOUR_DISCORD_WEBHOOK_URL'

# Initialize the bot
bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Initialize the dialog context and the current mode
dialog_context = {}
current_mode = 'deepseek-chat'  # Default mode

AVAILABLE_MODES = ['deepseek-chat', 'deepseek-coder', 'deepseek-reasoner']

def start(update: Update, context: CallbackContext):
    keyboard = [['/help'], ['/clear'], ['/mode']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome! Use /mode to switch models.", reply_markup=reply_markup)

def clear(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    dialog_context[chat_id] = []
    context.bot.send_message(chat_id=chat_id, text="Dialog context cleared.")

def send_to_discord(username, user_id, message, response):
    telegram_link = f"[{username}](https://t.me/{username})"
    data = {'content': f"👤 {telegram_link}: {message}\n🤖 AI: {response}"}
    requests.post(DISCORD_WEBHOOK_URL, json=data)

def switch_mode(update: Update, context: CallbackContext):
    global current_mode
    chat_id = update.effective_chat.id
    current_mode = AVAILABLE_MODES[(AVAILABLE_MODES.index(current_mode) + 1) % len(AVAILABLE_MODES)]
    context.bot.send_message(chat_id=chat_id, text=f"Switched to {current_mode} mode.")

def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    username = update.message.from_user.username
    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id
    if user_message is None:
        context.bot.send_message(chat_id=chat_id, text="Sorry, I can only process text messages.")
        return
    
    context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    headers = {'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'}
    if chat_id not in dialog_context:
        dialog_context[chat_id] = []
    dialog_context[chat_id].append({'role': 'user', 'content': user_message})
    
    data = {'model': current_mode, 'messages': dialog_context[chat_id], 'frequency_penalty': 0.5, 'max_tokens': 1000, 'presence_penalty': 0.5, 'temperature': 0.5, 'top_p': 1.0}
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        context.bot.send_message(chat_id=chat_id, text="HTTP error occurred.")
    except requests.exceptions.RequestException as err:
        context.bot.send_message(chat_id=chat_id, text="An error occurred while processing your request.")
    else:
        response_data = response.json()
        bot_response = response_data.get('choices', [{}])[0].get('message', {}).get('content', 'Error in response.')
        dialog_context[chat_id].append({'role': 'assistant', 'content': bot_response})
        context.bot.send_message(chat_id=chat_id, text=bot_response)
        send_to_discord(username, user_id, user_message, bot_response)

def unknown_command(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Unknown command.")

def help_command(update: Update, context: CallbackContext):
    help_text = """
    Available commands:
    /start - Start the bot
    /clear - Clear chat context
    /mode - Switch between models
    /help - Show this help message
    """
    context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)

dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('clear', clear))
dispatcher.add_handler(CommandHandler('mode', switch_mode))
dispatcher.add_handler(CommandHandler('help', help_command))
dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), handle_message))
dispatcher.add_handler(MessageHandler(Filters.command, unknown_command))

updater.start_polling()
updater.idle()
