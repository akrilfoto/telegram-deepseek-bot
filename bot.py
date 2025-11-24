import os
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class DeepSeekBot:
    def __init__(self):
        # Replit автоматически подставляет Secrets в переменные окружения
        self.token = os.environ['TELEGRAM_BOT_TOKEN']
        self.deepseek_api_key = os.environ['DEEPSEEK_API_KEY']
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
        # ЗАМЕНИ НА СВОЙ ТЕЛЕГРАМ ID!
        self.allowed_users = [155964417]  # ⚠️ ЗАМЕНИ НА СВОЙ ID!
        
        self.conversation_history = ""
    
    def is_user_allowed(self, user_id):
        return user_id in self.allowed_users
    
    def start(self, update, context):
        user_id = update.message.from_user.id
        
        if not self.is_user_allowed(user_id):
            update.message.reply_text("🚫 У вас нет доступа к этому боту.")
            return
        
        welcome_text = """
🤖 Привет! Я твой личный помощник с интеграцией DeepSeek!

Просто напиши мне вопрос, и я помогу!
        """
        update.message.reply_text(welcome_text)
    
    def help_command(self, update, context):
        user_id = update.message.from_user.id
        if not self.is_user_allowed(user_id):
            return
            
        help_text = "Просто напиши мне сообщение, и я обработаю его через DeepSeek API!"
        update.message.reply_text(help_text)
    
    def get_deepseek_response(self, user_message):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }
        
        messages = [{"role": "user", "content": user_message}]
        
        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "stream": False
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return f"⚠️ Ошибка: {str(e)}"
    
    def handle_message(self, update, context):
        user_id = update.message.from_user.id
        
        if not self.is_user_allowed(user_id):
            update.message.reply_text("🚫 У вас нет доступа к этому боту.")
            return
        
        user_message = update.message.text
        
        # Показываем, что бот печатает
        context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        response = self.get_deepseek_response(user_message)
        update.message.reply_text(response)
    
    def run(self):
        updater = Updater(self.token, use_context=True)
        dispatcher = updater.dispatcher
        
        dispatcher.add_handler(CommandHandler("start", self.start))
        dispatcher.add_handler(CommandHandler("help", self.help_command))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_message))
        
        logging.info("🤖 Бот запущен на Replit!")
        updater.start_polling()
        updater.idle()

# Запуск бота
if __name__ == "__main__":
    bot = DeepSeekBot()
    bot.run()
