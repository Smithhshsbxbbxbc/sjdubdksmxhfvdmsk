import logging
import os
from datetime import datetime
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

# Настройки бота
BOT_TOKEN = "8543231461:AAG8AeET0vjn6hxeG5nGf71O91CL_IYnJK8"
ADMIN_ID = "8495056620"  # ID администратора

# Состояния для ConversationHandler
GET_PRODUCT_NAME, GET_PRODUCT_QUANTITY = range(2)

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ShopBot:
    def __init__(self):
        self.orders = {}
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Отправляем фото с приветствием
        try:
            with open('start.png', 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=f"🌟 Добро пожаловать в Kristi Shop! 🌟\n\n"
                           f"Привет, {user.first_name}! 👋\n\n"
                           f"✨ Мы продаем:\n"
                           f"• Звезды ⭐\n"
                           f"• Доллары 💵 (@send)\n"
                           f"• И многое другое\n\n"
                           f"Выберите категорию товара:",
                    reply_markup=self.get_main_keyboard()
                )
        except FileNotFoundError:
            # Если фото не найдено, отправляем только текст
            await update.message.reply_text(
                f"🌟 Добро пожаловать в Kristi Shop! 🌟\n\n"
                f"Привет, {user.first_name}! 👋\n\n"
                f"✨ Мы продаем:\n"
                f"• Звезды ⭐\n"
                f"• Доллары 💵 (@send)\n"
                f"• И многое другое\n\n"
                f"Выберите категорию товара:",
                reply_markup=self.get_main_keyboard()
            )
    
    def get_main_keyboard(self):
        """Клавиатура главного меню"""
        keyboard = [
            [InlineKeyboardButton("⭐ Купить звезды", callback_data='buy_stars')],
            [InlineKeyboardButton("💵 Купить доллары", callback_data='buy_dollars')],
            [InlineKeyboardButton("🎁 Другое", callback_data='other')],
            [InlineKeyboardButton("👑 Админ панель", callback_data='admin_panel')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик нажатий кнопок"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        
        if query.data == 'buy_stars':
            await self.handle_stars_purchase(query)
        elif query.data == 'buy_dollars':
            await self.handle_dollars_purchase(query)
        elif query.data == 'other':
            await self.start_other_purchase(query)
        elif query.data == 'admin_panel':
            if user_id == ADMIN_ID:
                await self.show_admin_panel(query)
            else:
                await query.edit_message_text("⛔ У вас нет доступа к админ панели!")
        elif query.data == 'view_orders':
            await self.show_orders(query)
        elif query.data == 'clear_orders':
            await self.clear_orders(query)
        elif query.data == 'back_to_menu':
            await self.back_to_menu(query)
    
    async def handle_stars_purchase(self, query):
        """Обработка покупки звезд"""
        keyboard = [
            [InlineKeyboardButton("100 звезд - 1000₽", callback_data='stars_100')],
            [InlineKeyboardButton("500 звезд - 4500₽", callback_data='stars_500')],
            [InlineKeyboardButton("1000 звезд - 8000₽", callback_data='stars_1000')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
        ]
        
        await query.edit_message_text(
            "⭐ Выберите количество звезд:\n\n"
            "• 100 звезд - 1000₽\n"
            "• 500 звезд - 4500₽\n"
            "• 1000 звезд - 8000₽\n\n"
            "После выбора заказ будет отправлен администратору.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_dollars_purchase(self, query):
        """Обработка покупки долларов"""
        keyboard = [
            [InlineKeyboardButton("10$ - 1000₽", callback_data='dollars_10')],
            [InlineKeyboardButton("50$ - 4500₽", callback_data='dollars_50')],
            [InlineKeyboardButton("100$ - 8000₽", callback_data='dollars_100')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
        ]
        
        await query.edit_message_text(
            "💵 Выберите количество долларов (@send):\n\n"
            "• 10$ - 1000₽\n"
            "• 50$ - 4500₽\n"
            "• 100$ - 8000₽\n\n"
            "После выбора заказ будет отправлен администратору.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def start_other_purchase(self, query):
        """Начало покупки другого товара"""
        await query.edit_message_text(
            "🎁 Покупка другого товара\n\n"
            "Введите название товара:"
        )
        return GET_PRODUCT_NAME
    
    async def get_product_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получение названия товара"""
        product_name = update.message.text
        context.user_data['product_name'] = product_name
        
        await update.message.reply_text(
            f"Товар: {product_name}\n\n"
            f"Введите количество (или 'нет' если количество не требуется):"
        )
        return GET_PRODUCT_QUANTITY
    
    async def get_product_quantity(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получение количества товара"""
        quantity = update.message.text
        product_name = context.user_data.get('product_name', 'Неизвестный товар')
        
        # Сохраняем заказ
        user = update.effective_user
        order_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        order_info = {
            'id': order_id,
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'product': product_name,
            'quantity': quantity if quantity.lower() != 'нет' else '1',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Сохраняем заказ
        self.orders[order_id] = order_info
        
        # Отправляем заказ администратору
        await self.send_order_to_admin(order_info)
        
        # Отправляем подтверждение пользователю
        await update.message.reply_text(
            f"✅ Ваш заказ принят!\n\n"
            f"Товар: {product_name}\n"
            f"Количество: {quantity if quantity.lower() != 'нет' else '1'}\n\n"
            f"Администратор свяжется с вами в ближайшее время.",
            reply_markup=self.get_main_keyboard()
        )
        
        # Очищаем данные
        context.user_data.clear()
        return ConversationHandler.END
    
    async def send_order_to_admin(self, order_info: Dict[str, Any]) -> None:
        """Отправка заказа администратору"""
        try:
            # Здесь должна быть логика отправки сообщения администратору
            # В реальном боте используйте await context.bot.send_message()
            admin_message = (
                f"🛒 НОВЫЙ ЗАКАЗ #{order_info['id']}\n\n"
                f"👤 Пользователь: {order_info['first_name']}\n"
                f"📛 Username: @{order_info['username']}\n"
                f"🆔 ID: {order_info['user_id']}\n"
                f"🛍️ Товар: {order_info['product']}\n"
                f"🔢 Количество: {order_info['quantity']}\n"
                f"⏰ Время: {order_info['timestamp']}"
            )
            
            # В реальном боте раскомментируйте следующую строку:
            # await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
            
            logger.info(f"Заказ отправлен администратору: {admin_message}")
            print(f"\n{'='*50}")
            print(f"ЗАКАЗ ДЛЯ АДМИНИСТРАТОРА {ADMIN_ID}:")
            print(admin_message)
            print(f"{'='*50}\n")
            
        except Exception as e:
            logger.error(f"Ошибка отправки заказа администратору: {e}")
    
    async def show_admin_panel(self, query):
        """Показать админ панель"""
        keyboard = [
            [InlineKeyboardButton("📋 Просмотреть заказы", callback_data='view_orders')],
            [InlineKeyboardButton("🗑️ Очистить заказы", callback_data='clear_orders')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
        ]
        
        await query.edit_message_text(
            f"👑 АДМИН ПАНЕЛЬ\n\n"
            f"Всего заказов: {len(self.orders)}\n"
            f"Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_orders(self, query):
        """Показать список заказов"""
        if not self.orders:
            await query.edit_message_text(
                "📭 Список заказов пуст.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад в админку", callback_data='admin_panel')]
                ])
            )
            return
        
        orders_text = "📋 СПИСОК ЗАКАЗОВ:\n\n"
        for order_id, order in self.orders.items():
            orders_text += (
                f"#{order_id}\n"
                f"👤 {order['first_name']} (@{order['username']})\n"
                f"🛍️ {order['product']} x {order['quantity']}\n"
                f"⏰ {order['timestamp']}\n"
                f"{'-'*30}\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Очистить заказы", callback_data='clear_orders')],
            [InlineKeyboardButton("🔙 Назад в админку", callback_data='admin_panel')]
        ]
        
        await query.edit_message_text(
            orders_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def clear_orders(self, query):
        """Очистить список заказов"""
        self.orders.clear()
        await query.edit_message_text(
            "✅ Все заказы очищены!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад в админку", callback_data='admin_panel')]
            ])
        )
    
    async def back_to_menu(self, query):
        """Вернуться в главное меню"""
        user = query.from_user
        await query.edit_message_text(
            f"🌟 Kristi Shop\n\n"
            f"Привет, {user.first_name}! 👋\n\n"
            f"Выберите категорию товара:",
            reply_markup=self.get_main_keyboard()
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отмена диалога"""
        await update.message.reply_text(
            'Диалог отменен.',
            reply_markup=self.get_main_keyboard()
        )
        return ConversationHandler.END

def main() -> None:
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Создаем экземпляр бота
    bot = ShopBot()
    
    # ConversationHandler для покупки "другого" товара
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(bot.start_other_purchase, pattern='^other$')],
        states={
            GET_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_product_name)],
            GET_PRODUCT_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_product_quantity)],
        },
        fallbacks=[CommandHandler('cancel', bot.cancel)],
    )
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    # Запускаем бота
    print("Бот запущен...")
    print(f"ID администратора: {ADMIN_ID}")
    print("Ожидание сообщений...")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()