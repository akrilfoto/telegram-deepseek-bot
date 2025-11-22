import os
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Update
from dotenv import load_dotenv
import requests
import json

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class DeepSeekBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
        # Список разрешенных пользователей
        self.allowed_users = [
            155964417,  # ЗАМЕНИ НА СВОЙ ТЕЛЕГРАМ ID
        ]
        
        # Хранилище для истории диалогов
        self.conversation_history = ""
    
    def split_message(self, text, max_length=4000):
        """Разбивает длинное сообщение на части"""
        if len(text) <= max_length:
            return [text]
        
        parts = []
        while text:
            if len(text) <= max_length:
                parts.append(text)
                break
            else:
                # Ищем место для разрыва
                break_index = text.rfind('\n', 0, max_length)
                if break_index == -1:
                    break_index = text.rfind(' ', 0, max_length)
                if break_index == -1:
                    break_index = max_length
                    
                parts.append(text[:break_index])
                text = text[break_index:].lstrip()
        
        return parts

    def is_user_allowed(self, user_id):
        """Проверяет, есть ли пользователь в списке разрешенных"""
        return user_id in self.allowed_users
    
    def start(self, update, context):
        """Обработчик команды /start"""
        user_id = update.message.from_user.id
        
        if not self.is_user_allowed(user_id):
            update.message.reply_text("🚫 У вас нет доступа к этому боту.")
            return
        
        welcome_text = """
🤖 Привет! Я твой личный помощник с интеграцией DeepSeek!

Доступные команды:
/start - начать работу
/help - показать справку  
/upload_history - загрузить историю диалогов
/show_context - показать текущий контекст

Просто напиши мне вопрос, и я помогу!
        """
        update.message.reply_text(welcome_text)
    
    def help_command(self, update, context):
        """Обработчик команды /help"""
        user_id = update.message.from_user.id
        
        if not self.is_user_allowed(user_id):
            return
            
        help_text = """
📖 Доступные команды:
/start - начать работу
/help - показать эту справку
/upload_history - загрузить историю диалогов
/show_context - показать текущий контекст

Просто напиши сообщение, и я обработаю его через DeepSeek API!
        """
        update.message.reply_text(help_text)
    
    def upload_history_command(self, update, context):
        """Обработчик команды /upload_history"""
        user_id = update.message.from_user.id
        
        if not self.is_user_allowed(user_id):
            return
            
        instruction = """
📁 Отправь мне текстовый файл (.txt) с историей диалогов.

Советы по формату:
- Можно загружать несколько файлов - они объединятся
- Лучше сохранять диалоги в формате:
  Пользователь: текст
  Ассистент: текст
- Или просто текстом без разметки

Я запомню контекст и буду учитывать его в ответах!
"""
        update.message.reply_text(instruction)
    
    def show_context_command(self, update, context):
        """Показать текущий контекст"""
        user_id = update.message.from_user.id
        
        if not self.is_user_allowed(user_id):
            return
            
        if not self.conversation_history:
            update.message.reply_text("📝 Контекст пока пуст. Используй /upload_history чтобы загрузить историю.")
        else:
            preview = self.conversation_history[:500] + "..." if len(self.conversation_history) > 500 else self.conversation_history
            update.message.reply_text(f"📚 Текущий контекст ({len(self.conversation_history)} символов):\n\n{preview}")
    
    def handle_document(self, update, context):
        """Обработчик документов (загрузка истории)"""
        user_id = update.message.from_user.id
        
        if not self.is_user_allowed(user_id):
            return
            
        document = update.message.document
        
        # Проверяем что это текстовый файл
        if document.mime_type != "text/plain" and not document.file_name.endswith('.txt'):
            update.message.reply_text("❌ Пожалуйста, отправьте текстовый файл (.txt)")
            return
        
        update.message.reply_text("📥 Загружаю и анализирую историю...")
        
        try:
            # Скачиваем файл
            file = context.bot.get_file(document.file_id)
            file_path = file.download()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            # Добавляем к существующей истории
            if self.conversation_history:
                self.conversation_history += "\n\n" + text_content
            else:
                self.conversation_history = text_content
            
            update.message.reply_text(f"✅ История успешно загружена! Теперь контекст содержит {len(self.conversation_history)} символов.")
            
        except Exception as e:
            logging.error(f"Error processing history: {e}")
            update.message.reply_text("❌ Ошибка при обработке файла.")
    
    def get_deepseek_response(self, user_message):
        """Получаем ответ от DeepSeek API с учетом контекста"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }
        
        # Базовый системный промпт
        messages = [{
            "role": "system", 
            "content": "Ты полезный AI-ассистент. Отвечай дружелюбно и профессионально."
        }]
        
        # Добавляем контекст из истории, если он есть
        if self.conversation_history:
            context_message = f"""
Учти этот контекст из предыдущих диалогов с пользователем:
{self.conversation_history}

Отвечай в схожем стиле и учитывай историю общения.
"""
            messages.append({
                "role": "system",
                "content": context_message
            })
        
        # Добавляем текущее сообщение пользователя
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "stream": False
        }
        
        try:
            print(f"🔄 Отправляем запрос к DeepSeek API...")
            print(f"📝 Сообщение: {user_message}")
            
            response = requests.post(self.api_url, headers=headers, json=data, timeout=120)
            
            print(f"📡 Статус ответа: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            print("✅ Успешно получили ответ от API")
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP ошибка: {e}")
            return "⚠️ Ошибка API: Проверь API ключ и баланс"
            
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Ошибка соединения: {e}")
            return "⚠️ Ошибка соединения с API. Проверь интернет."
            
        except requests.exceptions.Timeout as e:
            print(f"❌ Таймаут: {e}")
            return "⚠️ Превышено время ожидания ответа от API."
            
        except Exception as e:
            print(f"❌ Неизвестная ошибка: {e}")
            return "⚠️ Произошла непредвиденная ошибка. Попробуй позже."
    
    def handle_message(self, update, context):
        """Обработчик текстовых сообщений"""
        user_id = update.message.from_user.id
        
        # Проверяем доступ
        if not self.is_user_allowed(user_id):
            update.message.reply_text("🚫 У вас нет доступа к этому боту.")
            return
        
        user_message = update.message.text
        
        # Показываем, что бот печатает
        context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Получаем ответ от DeepSeek
        response = self.get_deepseek_response(user_message)
        
        # Разбиваем длинные сообщения на части
        message_parts = self.split_message(response)

        # Отправляем каждую часть отдельным сообщением
        for part in message_parts:
            update.message.reply_text(part)
    
    def run(self):
        """Запуск бота"""
        updater = Updater(self.token, use_context=True)
        dispatcher = updater.dispatcher
        
        # Добавляем обработчики
        dispatcher.add_handler(CommandHandler("start", self.start))
        dispatcher.add_handler(CommandHandler("help", self.help_command))
        dispatcher.add_handler(CommandHandler("upload_history", self.upload_history_command))
        dispatcher.add_handler(CommandHandler("show_context", self.show_context_command))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_message))
        dispatcher.add_handler(MessageHandler(Filters.document, self.handle_document))
        
        # Запускаем бота
        logging.info("Бот запущен!")
        updater.start_polling()
        updater.idle()

if __name__ == "__main__":
    bot = DeepSeekBot()
    bot.run()
