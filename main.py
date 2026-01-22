import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
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
GET_PRODUCT_NAME, GET_PRODUCT_QUANTITY, GET_BROADCAST, WAITING_PAYMENT, ADMIN_RESPONSE = range(5)

# Файлы для хранения данных
ORDERS_FILE = "orders.json"
USERS_FILE = "users.json"

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ShopBot:
    def __init__(self):
        self.orders = self.load_orders()
        self.users = self.load_users()
        self.pending_payments = {}
        self.admin_conversations = {}  # Для отслеживания диалогов с админом
        
        # Цены
        self.prices = {
            'stars_100': {'name': '100 Telegram Stars ⭐', 'price': '153₽', 'photo': 'stars_100.png'},
            'stars_500': {'name': '500 Telegram Stars ⭐', 'price': '700₽', 'photo': 'stars_500.png'},
            'stars_1000': {'name': '1000 Telegram Stars ⭐', 'price': '1250₽', 'photo': 'stars_1000.png'},
            'stars_5000': {'name': '5000 Telegram Stars ⭐', 'price': '5500₽', 'photo': 'stars_5000.png'},
            'dollars_1': {'name': '1$ (@send) 💵', 'price': '83₽', 'photo': 'dollar_1.png'},
            'dollars_10': {'name': '10$ (@send) 💵', 'price': '800₽', 'photo': 'dollar_10.png'},
            'dollars_100': {'name': '100$ (@send) 💵', 'price': '7500₽', 'photo': 'dollar_100.png'},
            'premium_1': {'name': 'Telegram Premium (1 месяц)', 'price': '399₽', 'photo': 'premium.png'},
            'premium_12': {'name': 'Telegram Premium (12 месяцев)', 'price': '3999₽', 'photo': 'premium_year.png'}
        }
        
        # Категории товаров
        self.categories = {
            'stars': '⭐ Telegram Stars',
            'dollars': '💵 Доллары (@send)',
            'premium': '👑 Telegram Premium',
            'other': '🎁 Другие товары'
        }
    
    def load_orders(self):
        """Загрузка заказов из файла"""
        try:
            if os.path.exists(ORDERS_FILE):
                with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки заказов: {e}")
        return {}
    
    def save_orders(self):
        """Сохранение заказов в файл"""
        try:
            with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.orders, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения заказов: {e}")
    
    def load_users(self):
        """Загрузка пользователей из файла"""
        try:
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки пользователей: {e}")
        return {}
    
    def save_users(self):
        """Сохранение пользователей в файл"""
        try:
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения пользователей: {e}")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Сохраняем пользователя
        user_id = str(user.id)
        if user_id not in self.users:
            self.users[user_id] = {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'joined': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'orders': 0,
                'total_spent': 0,
                'last_active': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.save_users()
        else:
            # Обновляем время последней активности
            self.users[user_id]['last_active'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_users()
        
        # Отправляем фото с приветствием
        try:
            with open('start.png', 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=f"🌟 Добро пожаловать в Kristi Shop! 🌟\n\n"
                           f"Привет, {user.first_name}! 👋\n\n"
                           f"✨ Мы продаем:\n"
                           f"• Telegram Stars ⭐\n"
                           f"• Доллары 💵 (@send)\n"
                           f"• Telegram Premium 👑\n"
                           f"• И другие товары\n\n"
                           f"🎁 Выбирай товары, оформляй заказ!\n"
                           f"📞 Админ быстро свяжется с тобой!\n\n"
                           f"Выберите категорию товара:",
                    reply_markup=self.get_main_keyboard()
                )
        except FileNotFoundError:
            # Если фото не найдено, отправляем только текст
            await update.message.reply_text(
                f"🌟 Добро пожаловать в Kristi Shop! 🌟\n\n"
                f"Привет, {user.first_name}! 👋\n\n"
                f"✨ Мы продаем:\n"
                f"• Telegram Stars ⭐\n"
                f"• Доллары 💵 (@send)\n"
                f"• Telegram Premium 👑\n"
                f"• И другие товары\n\n"
                f"🎁 Выбирай товары, оформляй заказ!\n"
                f"📞 Админ быстро свяжется с тобой!\n\n"
                f"Выберите категорию товара:",
                reply_markup=self.get_main_keyboard()
            )
    
    def get_main_keyboard(self):
        """Клавиатура главного меню"""
        keyboard = [
            [InlineKeyboardButton("⭐ Telegram Stars", callback_data='category_stars')],
            [InlineKeyboardButton("💵 Доллары (@send)", callback_data='category_dollars')],
            [InlineKeyboardButton("👑 Telegram Premium", callback_data='category_premium')],
            [InlineKeyboardButton("🎁 Другие товары", callback_data='category_other')],
            [InlineKeyboardButton("📦 Мои заказы", callback_data='my_orders')],
            [InlineKeyboardButton("👑 Админ панель", callback_data='admin_panel')],
            [InlineKeyboardButton("📞 Поддержка", callback_data='support')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик нажатий кнопок"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        data = query.data
        
        # Обрабатываем разные типы кнопок
        if data.startswith('category_'):
            category = data.replace('category_', '')
            await self.show_category(query, category)
        elif data.startswith('buy_'):
            await self.process_standard_purchase(query, data.replace('buy_', ''), context)
        elif data == 'my_orders':
            await self.show_user_orders(query, user_id)
        elif data == 'admin_panel':
            if user_id == ADMIN_ID:
                await self.show_admin_panel(query)
            else:
                await query.message.reply_text("⛔ У вас нет доступа к админ панели!")
        elif data == 'support':
            await self.show_support(query)
        elif data == 'view_orders':
            await self.show_all_orders(query)
        elif data == 'view_users':
            await self.show_users(query)
        elif data == 'broadcast':
            await self.start_broadcast(query)
        elif data == 'stats':
            await self.show_stats(query)
        elif data == 'clear_orders':
            await self.clear_orders(query)
        elif data == 'back_to_menu':
            await self.back_to_menu(query)
        elif data == 'back_to_admin':
            await self.show_admin_panel(query)
        elif data == 'payment_done':
            await self.handle_payment_done(query, context)
        elif data == 'confirm_payment_':
            order_id = data.replace('confirm_payment_', '')
            await self.confirm_payment(query, order_id)
        elif data == 'respond_order_':
            order_id = data.replace('respond_order_', '')
            await self.start_admin_response(query, order_id)
    
    async def show_category(self, query, category):
        """Показать товары категории"""
        if category == 'stars':
            keyboard = [
                [InlineKeyboardButton("100 Stars - 153₽", callback_data='buy_stars_100')],
                [InlineKeyboardButton("500 Stars - 700₽", callback_data='buy_stars_500')],
                [InlineKeyboardButton("1000 Stars - 1250₽", callback_data='buy_stars_1000')],
                [InlineKeyboardButton("5000 Stars - 5500₽", callback_data='buy_stars_5000')],
                [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
            ]
            text = "⭐ Telegram Stars ⭐\n\nВыберите количество звезд:"
            
        elif category == 'dollars':
            keyboard = [
                [InlineKeyboardButton("1$ - 83₽", callback_data='buy_dollars_1')],
                [InlineKeyboardButton("10$ - 800₽", callback_data='buy_dollars_10')],
                [InlineKeyboardButton("100$ - 7500₽", callback_data='buy_dollars_100')],
                [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
            ]
            text = "💵 Доллары (@send) 💵\n\nВыберите количество долларов:"
            
        elif category == 'premium':
            keyboard = [
                [InlineKeyboardButton("Premium (1 месяц) - 399₽", callback_data='buy_premium_1')],
                [InlineKeyboardButton("Premium (12 месяцев) - 3999₽", callback_data='buy_premium_12')],
                [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
            ]
            text = "👑 Telegram Premium 👑\n\nВыберите вариант подписки:"
            
        elif category == 'other':
            await query.message.reply_text(
                "🎁 Другие товары\n\n"
                "Введите название товара:\n\n"
                "Для отмены введите /cancel"
            )
            return GET_PRODUCT_NAME
        
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def process_standard_purchase(self, query, product_key, context):
        """Обработка стандартной покупки"""
        product_info = self.prices.get(product_key, {})
        product_name = product_info.get('name', 'Неизвестный товар')
        price = product_info.get('price', 'Цена не указана')
        photo_file = product_info.get('photo', 'start.png')
        
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
            'status': 'новый',
            'type': 'стандартный',
            'payment_status': 'ожидает оплаты'
        }
        
        # Сохраняем заказ
        self.orders[order_id] = order_info
        self.save_orders()
        
        # Обновляем статистику пользователя
        user_id = str(user.id)
        if user_id in self.users:
            self.users[user_id]['orders'] = self.users[user_id].get('orders', 0) + 1
            self.save_users()
        
        # Отправляем фото товара и подтверждение
        try:
            with open(photo_file, 'rb') as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption=f"✅ Заказ оформлен!\n\n"
                           f"🛍️ Товар: {product_name}\n"
                           f"💰 Цена: {price}\n"
                           f"🆔 Номер заказа: #{order_id}\n\n"
                           f"📞 Администратор свяжется с вами для оплаты.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💳 Я оплатил", callback_data='payment_done')],
                        [InlineKeyboardButton("🛒 Сделать еще заказ", callback_data='back_to_menu')]
                    ])
                )
        except FileNotFoundError:
            await query.message.reply_text(
                f"✅ Заказ оформлен!\n\n"
                f"🛍️ Товар: {product_name}\n"
                f"💰 Цена: {price}\n"
                f"🆔 Номер заказа: #{order_id}\n\n"
                f"📞 Администратор свяжется с вами для оплаты.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Я оплатил", callback_data='payment_done')],
                    [InlineKeyboardButton("🛒 Сделать еще заказ", callback_data='back_to_menu')]
                ])
            )
        
        # Отправляем заказ администратору
        await self.send_order_to_admin(order_info, context)
    
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
            'status': 'новый',
            'type': 'другой товар',
            'payment_status': 'ожидает оплаты'
        }
        
        # Сохраняем заказ
        self.orders[order_id] = order_info
        self.save_orders()
        
        # Обновляем статистику пользователя
        user_id = str(user.id)
        if user_id in self.users:
            self.users[user_id]['orders'] = self.users[user_id].get('orders', 0) + 1
            self.save_users()
        
        # Отправляем подтверждение пользователю
        await update.message.reply_text(
            f"✅ Ваш заказ принят!\n\n"
            f"🛍️ Товар: {product_name}\n"
            f"🔢 Количество: {quantity if quantity.lower() != 'нет' else '1'}\n"
            f"🆔 Номер заказа: #{order_id}\n\n"
            f"📞 Администратор свяжется с вами в ближайшее время.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Я оплатил", callback_data='payment_done')],
                [InlineKeyboardButton("🛒 Сделать еще заказ", callback_data='back_to_menu')]
            ])
        )
        
        # Отправляем заказ администратору
        await self.send_order_to_admin(order_info, context)
        
        # Очищаем данные
        context.user_data.clear()
        return ConversationHandler.END
    
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
                f"💰 Цена: {order_info.get('price', 'уточнить у клиента')}\n"
                f"⏰ Время: {order_info['timestamp']}\n"
                f"📋 Статус: {order_info['status']}\n\n"
                f"Действия:"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("💬 Ответить", callback_data=f'respond_order_{order_info["id"]}'),
                    InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f'confirm_payment_{order_info["id"]}')
                ],
                [InlineKeyboardButton("👁️ Просмотреть заказ", callback_data='view_orders')]
            ]
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Сохраняем связь заказа с сообщением
            self.admin_conversations[order_info['id']] = {
                'user_id': order_info['user_id'],
                'order_id': order_info['id']
            }
            
        except Exception as e:
            logger.error(f"Ошибка отправки заказа администратору: {e}")
    
    async def handle_payment_done(self, query, context):
        """Пользователь нажал 'Я оплатил'"""
        user = query.from_user
        
        # Находим последний заказ пользователя
        user_orders = []
        for order_id, order in self.orders.items():
            if order['user_id'] == user.id and order['payment_status'] == 'ожидает оплаты':
                user_orders.append((order_id, order))
        
        if user_orders:
            # Берем последний заказ
            user_orders.sort(key=lambda x: x[1]['timestamp'], reverse=True)
            last_order_id, last_order = user_orders[0]
            
            # Уведомляем администратора
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"💳 ПОЛЬЗОВАТЕЛЬ ОПЛАТИЛ ЗАКАЗ #{last_order_id}\n\n"
                     f"👤 {user.first_name} (@{user.username})\n"
                     f"🛍️ Товар: {last_order['product']}\n"
                     f"💰 Цена: {last_order.get('price', 'уточнить')}\n\n"
                     f"Проверьте оплату и подтвердите заказ."
            )
            
            await query.message.reply_text(
                "✅ Уведомление об оплате отправлено администратору!\n\n"
                "Администратор проверит оплату и подтвердит ваш заказ."
            )
        else:
            await query.message.reply_text(
                "❌ Не найден ожидающий оплаты заказ.\n"
                "Возможно, ваш заказ уже обработан."
            )
    
    async def confirm_payment(self, query, order_id):
        """Администратор подтверждает оплату"""
        if order_id in self.orders:
            order = self.orders[order_id]
            order['payment_status'] = 'оплачено'
            order['status'] = 'оплачено'
            order['confirmed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_orders()
            
            # Уведомляем пользователя
            try:
                await query.bot.send_message(
                    chat_id=order['user_id'],
                    text=f"✅ Ваш заказ #{order_id} подтвержден!\n\n"
                         f"🛍️ Товар: {order['product']}\n"
                         f"💰 Цена: {order.get('price', 'уточнить')}\n"
                         f"⏰ Время подтверждения: {order['confirmed_at']}\n\n"
                         f"Спасибо за покупку! 🎉"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю: {e}")
            
            await query.message.reply_text(f"✅ Оплата заказа #{order_id} подтверждена!")
        else:
            await query.message.reply_text(f"❌ Заказ #{order_id} не найден!")
    
    async def start_admin_response(self, query, order_id):
        """Начало ответа администратора на заказ"""
        if order_id in self.orders:
            self.admin_conversations[order_id] = {
                'user_id': self.orders[order_id]['user_id'],
                'order_id': order_id,
                'waiting_response': True
            }
            await query.message.reply_text(
                f"💬 Ответ на заказ #{order_id}\n\n"
                f"Введите сообщение для пользователя:\n\n"
                f"Чтобы добавить кнопку 'Я оплатил', в конце сообщения добавьте #оплата\n\n"
                f"Для отмены введите /cancel"
            )
            return ADMIN_RESPONSE
        else:
            await query.message.reply_text("❌ Заказ не найден!")
    
    async def handle_admin_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка ответа администратора"""
        message_text = update.message.text
        user_id = str(update.effective_user.id)
        
        if user_id != ADMIN_ID:
            await update.message.reply_text("⛔ У вас нет прав для этой операции!")
            return ConversationHandler.END
        
        # Ищем заказ, для которого идет ответ
        current_order_id = None
        for order_id, conv in self.admin_conversations.items():
            if conv.get('waiting_response'):
                current_order_id = order_id
                break
        
        if not current_order_id or current_order_id not in self.orders:
            await update.message.reply_text("❌ Диалог не найден или заказ удален!")
            return ConversationHandler.END
        
        order = self.orders[current_order_id]
        
        # Проверяем, есть ли #оплата в конце сообщения
        has_payment_button = message_text.strip().endswith('#оплата')
        if has_payment_button:
            # Убираем #оплата из текста
            message_text = message_text.replace('#оплата', '').strip()
        
        try:
            # Отправляем сообщение пользователю
            user_message = f"💬 Сообщение от администратора по заказу #{current_order_id}:\n\n{message_text}"
            
            if has_payment_button:
                keyboard = [[InlineKeyboardButton("💳 Я оплатил", callback_data='payment_done')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
            else:
                reply_markup = None
            
            await context.bot.send_message(
                chat_id=order['user_id'],
                text=user_message,
                reply_markup=reply_markup
            )
            
            # Обновляем историю заказа
            if 'admin_messages' not in order:
                order['admin_messages'] = []
            
            order['admin_messages'].append({
                'text': message_text,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'has_payment_button': has_payment_button
            })
            self.save_orders()
            
            await update.message.reply_text(
                f"✅ Сообщение отправлено пользователю @{order['username']}!\n"
                f"📝 Кнопка 'Я оплатил': {'✅ добавлена' if has_payment_button else '❌ не добавлена'}"
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю: {e}")
            await update.message.reply_text(f"❌ Ошибка отправки сообщения: {e}")
        
        # Завершаем диалог
        if current_order_id in self.admin_conversations:
            self.admin_conversations[current_order_id]['waiting_response'] = False
        
        return ConversationHandler.END
    
    async def show_admin_panel(self, query):
        """Показать админ панель"""
        total_orders = len(self.orders)
        total_users = len(self.users)
        
        # Считаем статистику
        new_orders = sum(1 for order in self.orders.values() if order['status'] == 'новый')
        pending_payments = sum(1 for order in self.orders.values() if order['payment_status'] == 'ожидает оплаты')
        
        keyboard = [
            [InlineKeyboardButton("📋 Все заказы", callback_data='view_orders')],
            [InlineKeyboardButton("👥 Все пользователи", callback_data='view_users')],
            [InlineKeyboardButton("📢 Рассылка", callback_data='broadcast')],
            [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
            [InlineKeyboardButton("🗑️ Очистить заказы", callback_data='clear_orders')],
            [InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_menu')]
        ]
        
        await query.message.reply_text(
            f"👑 АДМИН ПАНЕЛЬ\n\n"
            f"📊 Статистика:\n"
            f"• Всего заказов: {total_orders}\n"
            f"• Новые заказы: {new_orders}\n"
            f"• Ожидают оплаты: {pending_payments}\n"
            f"• Всего пользователей: {total_users}\n\n"
            f"Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_all_orders(self, query):
        """Показать все заказы"""
        if not self.orders:
            await query.message.reply_text("📭 Список заказов пуст.")
            return
        
        orders_text = "📋 ВСЕ ЗАКАЗЫ:\n\n"
        for i, (order_id, order) in enumerate(list(self.orders.items())[-20:], 1):
            status_emoji = "🟢" if order['status'] == 'оплачено' else "🟡" if order['status'] == 'новый' else "🔴"
            payment_emoji = "✅" if order['payment_status'] == 'оплачено' else "⏳"
            
            orders_text += (
                f"{i}. #{order_id} {status_emoji}{payment_emoji}\n"
                f"   👤 {order['first_name']} (@{order['username']})\n"
                f"   🛍️ {order['product']}\n"
                f"   💰 {order.get('price', 'уточнить')}\n"
                f"   ⏰ {order['timestamp']}\n"
                f"{'-'*50}\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(orders_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_users(self, query):
        """Показать всех пользователей"""
        if not self.users:
            await query.message.reply_text("👥 Список пользователей пуст.")
            return
        
        users_text = "👥 ВСЕ ПОЛЬЗОВАТЕЛИ:\n\n"
        for i, (user_id, user) in enumerate(list(self.users.items())[-15:], 1):
            orders_count = user.get('orders', 0)
            users_text += (
                f"{i}. {user['first_name']} (@{user.get('username', 'без username')})\n"
                f"   🆔 ID: {user_id}\n"
                f"   🛍️ Заказов: {orders_count}\n"
                f"   📅 Регистрация: {user.get('joined', 'неизвестно')}\n"
                f"{'-'*40}\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("📢 Рассылка", callback_data='broadcast')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(users_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def start_broadcast(self, query):
        """Начало рассылки"""
        await query.message.reply_text(
            "📢 РАССЫЛКА ВСЕМ ПОЛЬЗОВАТЕЛЯМ\n\n"
            "Введите сообщение для рассылки:\n\n"
            "Для отмены введите /cancel"
        )
        return GET_BROADCAST
    
    async def handle_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка рассылки"""
        message_text = update.message.text
        user_id = str(update.effective_user.id)
        
        if user_id != ADMIN_ID:
            await update.message.reply_text("⛔ У вас нет прав для рассылки!")
            return ConversationHandler.END
        
        # Статистика рассылки
        total_users = len(self.users)
        sent = 0
        failed = 0
        
        await update.message.reply_text(f"📤 Начинаю рассылку для {total_users} пользователей...")
        
        for uid, user in self.users.items():
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=f"📢 Сообщение от Kristi Shop:\n\n{message_text}"
                )
                sent += 1
            except Exception as e:
                logger.error(f"Ошибка отправки пользователю {uid}: {e}")
                failed += 1
        
        await update.message.reply_text(
            f"✅ Рассылка завершена!\n\n"
            f"📊 Статистика:\n"
            f"• Всего пользователей: {total_users}\n"
            f"• Успешно отправлено: {sent}\n"
            f"• Не отправлено: {failed}\n"
            f"• Процент доставки: {sent/total_users*100:.1f}%"
        )
        
        return ConversationHandler.END
    
    async def show_stats(self, query):
        """Показать статистику"""
        total_orders = len(self.orders)
        total_users = len(self.users)
        
        # Статистика по статусам
        status_stats = {}
        payment_stats = {}
        
        for order in self.orders.values():
            status = order.get('status', 'неизвестно')
            payment = order.get('payment_status', 'неизвестно')
            
            status_stats[status] = status_stats.get(status, 0) + 1
            payment_stats[payment] = payment_stats.get(payment, 0) + 1
        
        # Активные пользователи (последние 7 дней)
        week_ago = datetime.now().timestamp() - 7 * 24 * 3600
        active_users = 0
        
        for user in self.users.values():
            last_active = user.get('last_active')
            if last_active:
                try:
                    last_active_dt = datetime.strptime(last_active, "%Y-%m-%d %H:%M:%S")
                    if last_active_dt.timestamp() > week_ago:
                        active_users += 1
                except:
                    pass
        
        stats_text = (
            f"📊 СТАТИСТИКА БОТА\n\n"
            f"👥 Пользователи:\n"
            f"• Всего: {total_users}\n"
            f"• Активные (7 дней): {active_users}\n\n"
            f"🛍️ Заказы:\n"
            f"• Всего: {total_orders}\n"
        )
        
        # Добавляем статистику по статусам
        for status, count in status_stats.items():
            stats_text += f"• {status}: {count}\n"
        
        stats_text += f"\n💳 Статусы оплаты:\n"
        for payment, count in payment_stats.items():
            stats_text += f"• {payment}: {count}\n"
        
        keyboard = [
            [InlineKeyboardButton("📋 Заказы", callback_data='view_orders')],
            [InlineKeyboardButton("👥 Пользователи", callback_data='view_users')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_user_orders(self, query, user_id):
        """Показать заказы пользователя"""
        user_orders = []
        for order_id, order in self.orders.items():
            if str(order['user_id']) == user_id:
                user_orders.append((order_id, order))
        
        if not user_orders:
            await query.message.reply_text(
                "📭 У вас еще нет заказов.\n"
                "Сделайте свой первый заказ! 🛍️",
                reply_markup=self.get_main_keyboard()
            )
            return
        
        user_orders.sort(key=lambda x: x[1]['timestamp'], reverse=True)
        
        orders_text = f"📦 ВАШИ ЗАКАЗЫ ({len(user_orders)}):\n\n"
        for i, (order_id, order) in enumerate(user_orders[:10], 1):
            status_emoji = "✅" if order['payment_status'] == 'оплачено' else "⏳"
            orders_text += (
                f"{i}. #{order_id} {status_emoji}\n"
                f"   🛍️ {order['product']}\n"
                f"   💰 {order.get('price', 'уточнить')}\n"
                f"   ⏰ {order['timestamp']}\n"
                f"   📋 Статус: {order['payment_status']}\n"
                f"{'-'*40}\n"
            )
        
        if len(user_orders) > 10:
            orders_text += f"\n... и еще {len(user_orders) - 10} заказов"
        
        keyboard = [
            [InlineKeyboardButton("🛒 Сделать заказ", callback_data='back_to_menu')],
            [InlineKeyboardButton("📞 Поддержка", callback_data='support')]
        ]
        
        await query.message.reply_text(orders_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_support(self, query):
        """Показать информацию о поддержке"""
        await query.message.reply_text(
            "📞 ПОДДЕРЖКА\n\n"
            "Если у вас есть вопросы или проблемы:\n\n"
            "1. По заказам - администратор свяжется с вами\n"
            "2. По оплате - используйте кнопку 'Я оплатил'\n"
            "3. По другим вопросам - напишите администратору\n\n"
            "Администратор: @admin_username\n\n"
            "Мы всегда рады помочь! 💫",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Сделать заказ", callback_data='back_to_menu')],
                [InlineKeyboardButton("📦 Мои заказы", callback_data='my_orders')]
            ])
        )
    
    async def clear_orders(self, query):
        """Очистить список заказов"""
        keyboard = [
            [InlineKeyboardButton("✅ Да, очистить", callback_data='confirm_clear')],
            [InlineKeyboardButton("❌ Нет, отмена", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(
            f"⚠️ ВЫ УВЕРЕНЫ?\n\n"
            f"Будет удалено {len(self.orders)} заказов.\n"
            f"Это действие нельзя отменить!\n\n"
            f"Подтвердите очистку:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def back_to_menu(self, query):
        """Вернуться в главное меню"""
        user = query.from_user
        await query.message.reply_text(
            f"🌟 Kristi Shop\n\n"
            f"Привет, {user.first_name}! 👋\n\n"
            f"✨ Мы продаем:\n"
            f"• Telegram Stars ⭐\n"
            f"• Доллары 💵 (@send)\n"
            f"• Telegram Premium 👑\n"
            f"• И другие товары\n\n"
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
    other_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(bot.show_category, pattern='^category_other$')],
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
    
    # ConversationHandler для рассылки
    broadcast_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(bot.start_broadcast, pattern='^broadcast$')],
        states={
            GET_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_broadcast)
            ],
        },
        fallbacks=[CommandHandler('cancel', bot.cancel)],
    )
    
    # ConversationHandler для ответа администратора
    admin_response_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(bot.start_admin_response, pattern='^respond_order_')],
        states={
            ADMIN_RESPONSE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_admin_response)
            ],
        },
        fallbacks=[CommandHandler('cancel', bot.cancel)],
    )
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(other_handler)
    application.add_handler(broadcast_handler)
    application.add_handler(admin_response_handler)
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    # Команда отмены
    application.add_handler(CommandHandler("cancel", bot.cancel))
    
    # Запускаем бота
    print("="*70)
    print("🤖 Бот Kristi Shop запущен!")
    print(f"🔑 Токен: {BOT_TOKEN[:15]}...")
    print(f"👑 Администратор: {ADMIN_ID}")
    print("="*70)
    print("\n💰 ЦЕНЫ:")
    print("  ⭐ Telegram Stars:")
    print("    • 100 Stars - 153₽")
    print("    • 500 Stars - 700₽")
    print("    • 1000 Stars - 1250₽")
    print("    • 5000 Stars - 5500₽")
    print("  💵 Доллары (@send):")
    print("    • 1$ - 83₽")
    print("    • 10$ - 800₽")
    print("    • 100$ - 7500₽")
    print("  👑 Telegram Premium:")
    print("    • 1 месяц - 399₽")
    print("    • 12 месяцев - 3999₽")
    print("="*70)
    print("\n📁 НЕОБХОДИМЫЕ ФАЙЛЫ ДЛЯ ФОТО:")
    print("1. start.png - фото для стартового сообщения")
    print("2. stars_100.png - фото для 100 звезд")
    print("3. stars_500.png - фото для 500 звезд")
    print("4. stars_1000.png - фото для 1000 звезд")
    print("5. stars_5000.png - фото для 5000 звезд")
    print("6. dollar_1.png - фото для 1$")
    print("7. dollar_10.png - фото для 10$")
    print("8. dollar_100.png - фото для 100$")
    print("9. premium.png - фото для Telegram Premium")
    print("10. premium_year.png - фото для годовой подписки")
    print("="*70)
    print("\n🎯 ФУНКЦИОНАЛ:")
    print("• Товары с фото и описанием")
    print("• Заказы с отслеживанием статуса")
    print("• Кнопка 'Я оплатил' для пользователей")
    print("• Подтверждение оплаты администратором")
    print("• Ответы администратора на заказы")
    print("• Рассылка всем пользователям")
    print("• Статистика и админ панель")
    print("• История заказов пользователей")
    print("="*70)
    print("\nОжидание сообщений...\n")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()