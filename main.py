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
        # Исправленные цены по вашим данным
        self.prices = {
            'stars_100': {'name': '100 звезд', 'price': '153₽'},
            'stars_500': {'name': '500 звезд', 'price': '700₽'},
            'stars_1000': {'name': '1000 звезд', 'price': '1250₽'},
            'dollars_1': {'name': '1$ (@send)', 'price': '83₽'},
            'dollars_10': {'name': '10$ (@send)', 'price': '800₽'},
            'dollars_100': {'name': '100$ (@send)', 'price': '7500₽'}
        }
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Отправляем приветственное сообщение с кнопками
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
        data = query.data
        
        # Обрабатываем разные типы кнопок
        if data == 'buy_stars':
            await self.handle_stars_purchase(query)
        elif data == 'buy_dollars':
            await self.handle_dollars_purchase(query)
        elif data == 'other':
            await self.start_other_purchase(query)
        elif data == 'admin_panel':
            if user_id == ADMIN_ID:
                await self.show_admin_panel(query)
            else:
                await query.message.reply_text(
                    "⛔ У вас нет доступа к админ панели!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
                    ])
                )
        elif data in ['stars_100', 'stars_500', 'stars_1000', 
                     'dollars_1', 'dollars_10', 'dollars_100']:
            await self.process_standard_purchase(query, data, context)
        elif data == 'view_orders':
            await self.show_orders(query)
        elif data == 'clear_orders':
            await self.clear_orders(query)
        elif data == 'back_to_menu':
            await self.back_to_menu(query)
        elif data == 'back_to_admin':
            await self.show_admin_panel(query)
    
    async def handle_stars_purchase(self, query):
        """Обработка покупки звезд"""
        keyboard = [
            [InlineKeyboardButton("100 звезд - 153₽", callback_data='stars_100')],
            [InlineKeyboardButton("500 звезд - 700₽", callback_data='stars_500')],
            [InlineKeyboardButton("1000 звезд - 1250₽", callback_data='stars_1000')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
        ]
        
        await query.message.reply_text(
            "⭐ Выберите количество звезд:\n\n"
            "• 100 звезд - 153₽\n"
            "• 500 звезд - 700₽\n"
            "• 1000 звезд - 1250₽\n\n"
            "После выбора заказ будет отправлен администратору.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_dollars_purchase(self, query):
        """Обработка покупки долларов"""
        keyboard = [
            [InlineKeyboardButton("1$ - 83₽", callback_data='dollars_1')],
            [InlineKeyboardButton("10$ - 800₽", callback_data='dollars_10')],
            [InlineKeyboardButton("100$ - 7500₽", callback_data='dollars_100')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
        ]
        
        await query.message.reply_text(
            "💵 Выберите количество долларов (@send):\n\n"
            "• 1$ - 83₽\n"
            "• 10$ - 800₽\n"
            "• 100$ - 7500₽\n\n"
            "После выбора заказ будет отправлен администратору.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def start_other_purchase(self, query):
        """Начало покупки другого товара"""
        await query.message.reply_text(
            "🎁 Покупка другого товара\n\n"
            "Введите название товара:\n\n"
            "Для отмены введите /cancel"
        )
        return GET_PRODUCT_NAME
    
    async def get_product_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получение названия товара"""
        product_name = update.message.text
        context.user_data['product_name'] = product_name
        
        await update.message.reply_text(
            f"Товар: {product_name}\n\n"
            f"Введите количество (или 'нет' если количество не требуется):\n\n"
            f"Для отмены введите /cancel"
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
            'username': user.username or 'без username',
            'first_name': user.first_name,
            'product': product_name,
            'quantity': quantity if quantity.lower() != 'нет' else '1',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'type': 'другой товар'
        }
        
        # Сохраняем заказ
        self.orders[order_id] = order_info
        
        # Отправляем заказ администратору
        await self.send_order_to_admin(order_info, context)
        
        # Отправляем подтверждение пользователю
        await update.message.reply_text(
            f"✅ Ваш заказ принят!\n\n"
            f"🛍️ Товар: {product_name}\n"
            f"🔢 Количество: {quantity if quantity.lower() != 'нет' else '1'}\n\n"
            f"📞 Администратор свяжется с вами в ближайшее время.",
            reply_markup=self.get_main_keyboard()
        )
        
        # Очищаем данные
        context.user_data.clear()
        return ConversationHandler.END
    
    async def process_standard_purchase(self, query, product_key, context):
        """Обработка стандартной покупки (звезды/доллары)"""
        product_info = self.prices.get(product_key, {})
        product_name = product_info.get('name', 'Неизвестный товар')
        price = product_info.get('price', 'Цена не указана')
        
        user = query.from_user
        order_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        order_info = {
            'id': order_id,
            'user_id': user.id,
            'username': user.username or 'без username',
            'first_name': user.first_name,
            'product': product_name,
            'quantity': '1',
            'price': price,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'type': 'стандартный товар'
        }
        
        # Сохраняем заказ
        self.orders[order_id] = order_info
        
        # Отправляем заказ администратору
        await self.send_order_to_admin(order_info, context)
        
        # Отправляем подтверждение пользователю
        await query.message.reply_text(
            f"✅ Заказ оформлен!\n\n"
            f"🛍️ Товар: {product_name}\n"
            f"💰 Цена: {price}\n\n"
            f"📞 Администратор свяжется с вами для оплаты.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Сделать еще заказ", callback_data='back_to_menu')]
            ])
        )
    
    async def send_order_to_admin(self, order_info: Dict[str, Any], context: ContextTypes.DEFAULT_TYPE) -> None:
        """Отправка заказа администратору"""
        try:
            admin_message = (
                f"🛒 НОВЫЙ ЗАКАЗ #{order_info['id']}\n\n"
                f"👤 Пользователь: {order_info['first_name']}\n"
                f"📛 Username: @{order_info['username']}\n"
                f"🆔 ID: {order_info['user_id']}\n"
                f"🛍️ Товар: {order_info['product']}\n"
                f"🔢 Количество: {order_info['quantity']}\n"
                f"⏰ Время: {order_info['timestamp']}\n"
                f"📋 Тип: {order_info.get('type', 'неизвестно')}"
            )
            
            if 'price' in order_info:
                admin_message += f"\n💰 Цена: {order_info['price']}"
            
            # Печатаем в консоль для демонстрации
            self.print_order_to_console(order_info)
            
            # Отправляем сообщение администратору
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
            
        except Exception as e:
            logger.error(f"Ошибка отправки заказа администратору: {e}")
    
    def print_order_to_console(self, order_info):
        """Печать заказа в консоль"""
        print("\n" + "="*60)
        print(f"📦 НОВЫЙ ЗАКАЗ ДЛЯ АДМИНИСТРАТОРА {ADMIN_ID}:")
        print("="*60)
        print(f"🆔 ID заказа: #{order_info['id']}")
        print(f"👤 Пользователь: {order_info['first_name']}")
        print(f"📛 Username: @{order_info['username']}")
        print(f"🆔 User ID: {order_info['user_id']}")
        print(f"🛍️ Товар: {order_info['product']}")
        print(f"💰 Цена: {order_info.get('price', 'не указана')}")
        print(f"🔢 Количество: {order_info['quantity']}")
        print(f"⏰ Время: {order_info['timestamp']}")
        print("="*60 + "\n")
    
    async def show_admin_panel(self, query):
        """Показать админ панель"""
        keyboard = [
            [InlineKeyboardButton("📋 Просмотреть заказы", callback_data='view_orders')],
            [InlineKeyboardButton("🗑️ Очистить заказы", callback_data='clear_orders')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
        ]
        
        await query.message.reply_text(
            f"👑 АДМИН ПАНЕЛЬ\n\n"
            f"Всего заказов: {len(self.orders)}\n"
            f"Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_orders(self, query):
        """Показать список заказов"""
        if not self.orders:
            keyboard = [[InlineKeyboardButton("🔙 Назад в админку", callback_data='back_to_admin')]]
            await query.message.reply_text(
                "📭 Список заказов пуст.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        orders_text = "📋 СПИСОК ЗАКАЗОВ:\n\n"
        for i, (order_id, order) in enumerate(list(self.orders.items())[-10:], 1):
            orders_text += (
                f"{i}. #{order_id}\n"
                f"   👤 {order['first_name']} (@{order['username']})\n"
                f"   🛍️ {order['product']}\n"
                f"   🔢 {order['quantity']} шт.\n"
                f"   ⏰ {order['timestamp']}\n"
                f"{'-'*40}\n"
            )
        
        if len(self.orders) > 10:
            orders_text += f"\n... и еще {len(self.orders) - 10} заказов"
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Очистить заказы", callback_data='clear_orders')],
            [InlineKeyboardButton("🔙 Назад в админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(
            orders_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def clear_orders(self, query):
        """Очистить список заказов"""
        self.orders.clear()
        keyboard = [[InlineKeyboardButton("🔙 Назад в админку", callback_data='back_to_admin')]]
        await query.message.reply_text(
            "✅ Все заказы очищены!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def back_to_menu(self, query):
        """Вернуться в главное меню"""
        user = query.from_user
        await query.message.reply_text(
            f"🌟 Kristi Shop\n\n"
            f"Приет, {user.first_name}! 👋\n\n"
            f"✨ Мы продаем:\n"
            f"• Звезды ⭐\n"
            f"• Доллары 💵 (@send)\n"
            f"• И многое другое\n\n"
            f"Выберите категорию товара:",
            reply_markup=self.get_main_keyboard()
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отмена диалога"""
        await update.message.reply_text(
            '❌ Диалог отменен.',
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
        entry_points=[
            CallbackQueryHandler(bot.start_other_purchase, pattern='^other$')
        ],
        states={
            GET_PRODUCT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_product_name)
            ],
            GET_PRODUCT_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_product_quantity)
            ],
        },
        fallbacks=[CommandHandler('cancel', bot.cancel)],
    )
    
    # Регистрируем обработчики в правильном порядке
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(conv_handler)
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    # Команда отмены
    application.add_handler(CommandHandler("cancel", bot.cancel))
    
    # Запускаем бота
    print("="*60)
    print("🤖 Бот Kristi Shop запущен!")
    print(f"🔑 Токен: {BOT_TOKEN[:15]}...")
    print(f"👑 Администратор: {ADMIN_ID}")
    print("💰 Цены:")
    print("  100 звезд - 153₽")
    print("  500 звезд - 700₽")
    print("  1000 звезд - 1250₽")
    print("  1$ - 83₽")
    print("  10$ - 800₽")
    print("  100$ - 7500₽")
    print("="*60)
    print("\nОжидание сообщений...\n")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()