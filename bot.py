# main.py

import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv
from helpers.menu_handlers import (
    start,
    show_main_menu,
    receive_wallet_address,
    main_menu_handler,
    remove_wallet,
    stop_tracking,
    toggle_wallet,
    back_to_main_menu,
    user_data,  # Ensure user_data is shared
)

# Load environment variables
load_dotenv()
# Get the TELEGRAM_TOKEN from the environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARNING)
logger = logging.getLogger(__name__)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", show_main_menu))

    # Callback query handlers
    application.add_handler(CallbackQueryHandler(main_menu_handler, pattern='^(add_wallet|view_wallets|start_tracking|back_to_main)$'))
    application.add_handler(CallbackQueryHandler(remove_wallet, pattern='^remove_wallet_'))
    application.add_handler(CallbackQueryHandler(stop_tracking, pattern='^stop_tracking$'))
    application.add_handler(CallbackQueryHandler(toggle_wallet, pattern='^toggle_wallet_'))

    # Message handler for receiving wallet address and name
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_wallet_address))

    application.run_polling()

if __name__ == '__main__':
    main()
