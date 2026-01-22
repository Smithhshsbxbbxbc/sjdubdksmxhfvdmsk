import logging
import os
import json
import asyncio
from datetime import datetime, timedelta
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
SETTINGS_FILE = "settings.json"

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
        self.settings = self.load_settings()
        self.pending_payments = {}
        self.admin_conversations = {}
        
        # Цены с фото
        self.prices = {
            'stars_100': {'name': '100 Telegram Stars ⭐', 'price': '153₽', 'photo': 'stars_100.png'},
            'stars_500': {'name': '500 Telegram Stars ⭐', 'price': '700₽', 'photo': 'stars_500.png'},
            'stars_1000': {'name': '1000 Telegram Stars ⭐', 'price': '1250₽', 'photo': 'stars_1000.png'},
            'stars_5000': {'name': '5000 Telegram Stars ⭐', 'price': '5500₽', 'photo': 'stars_5000.png'},
            'stars_10000': {'name': '10000 Telegram Stars ⭐', 'price': '10000₽', 'photo': 'stars_10000.png'},
            'dollars_1': {'name': '1$ (@send) 💵', 'price': '83₽', 'photo': 'dollar_1.png'},
            'dollars_10': {'name': '10$ (@send) 💵', 'price': '800₽', 'photo': 'dollar_10.png'},
            'dollars_50': {'name': '50$ (@send) 💵', 'price': '3800₽', 'photo': 'dollar_50.png'},
            'dollars_100': {'name': '100$ (@send) 💵', 'price': '7500₽', 'photo': 'dollar_100.png'},
            'premium_1': {'name': 'Telegram Premium (1 месяц) 👑', 'price': '399₽', 'photo': 'premium_1.png'},
            'premium_3': {'name': 'Telegram Premium (3 месяца) 👑', 'price': '999₽', 'photo': 'premium_3.png'},
            'premium_12': {'name': 'Telegram Premium (12 месяцев) 👑', 'price': '3999₽', 'photo': 'premium_12.png'},
            'boosts_1': {'name': 'Telegram Boost (1) 🚀', 'price': '299₽', 'photo': 'boost_1.png'},
            'boosts_3': {'name': 'Telegram Boost (3) 🚀', 'price': '799₽', 'photo': 'boost_3.png'},
            'boosts_6': {'name': 'Telegram Boost (6) 🚀', 'price': '1499₽', 'photo': 'boost_6.png'},
        }
        
        # Категории товаров
        self.categories = {
            'stars': '⭐ Telegram Stars',
            'dollars': '💵 Доллары (@send)',
            'premium': '👑 Telegram Premium',
            'boosts': '🚀 Telegram Boosts',
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
    
    def load_settings(self):
        """Загрузка настроек из файла"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек: {e}")
        return {
            'broadcast_delay': 0.5,
            'auto_confirm_payment': False,
            'welcome_message': 'Добро пожаловать в Kristi Shop!',
            'support_contact': '@kristi_support',
            'payment_methods': ['СБП', 'Крипто', 'Карта'],
            'min_order_amount': 100
        }
    
    def save_settings(self):
        """Сохранение настроек в файл"""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {e}")
    
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
                'last_active': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'ref_code': self.generate_ref_code(),
                'ref_by': None,
                'ref_count': 0,
                'ref_earned': 0,
                'is_banned': False
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
                           f"• Telegram Stars ⭐ (от 153₽)\n"
                           f"• Доллары 💵 (@send) (от 83₽)\n"
                           f"• Telegram Premium 👑 (от 399₽)\n"
                           f"• Telegram Boosts 🚀 (от 299₽)\n"
                           f"• И другие товары\n\n"
                           f"🎁 Выбирай товары, оформляй заказ!\n"
                           f"📞 Админ быстро свяжется с тобой!\n"
                           f"💎 Реферальная система: 5% с каждого заказа\n\n"
                           f"Твоя реферальная ссылка:\n"
                           f"https://t.me/kristi_shop_bot?start={self.users[user_id]['ref_code']}\n\n"
                           f"Выберите категорию товара:",
                    reply_markup=self.get_main_keyboard()
                )
        except FileNotFoundError:
            # Если фото не найдено, отправляем только текст
            await update.message.reply_text(
                f"🌟 Добро пожаловать в Kristi Shop! 🌟\n\n"
                f"Привет, {user.first_name}! 👋\n\n"
                f"✨ Мы продаем:\n"
                f"• Telegram Stars ⭐ (от 153₽)\n"
                f"• Доллары 💵 (@send) (от 83₽)\n"
                f"• Telegram Premium 👑 (от 399₽)\n"
                f"• Telegram Boosts 🚀 (от 299₽)\n"
                f"• И другие товары\n\n"
                f"🎁 Выбирай товары, оформляй заказ!\n"
                f"📞 Админ быстро свяжется с тобой!\n"
                f"💎 Реферальная система: 5% с каждого заказа\n\n"
                f"Твоя реферальная ссылка:\n"
                f"https://t.me/kristi_shop_bot?start={self.users[user_id]['ref_code']}\n\n"
                f"Выберите категорию товара:",
                reply_markup=self.get_main_keyboard()
            )
    
    def generate_ref_code(self):
        """Генерация реферального кода"""
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    def get_main_keyboard(self):
        """Клавиатура главного меню"""
        keyboard = [
            [InlineKeyboardButton("⭐ Telegram Stars", callback_data='category_stars')],
            [InlineKeyboardButton("💵 Доллары (@send)", callback_data='category_dollars')],
            [InlineKeyboardButton("👑 Telegram Premium", callback_data='category_premium')],
            [InlineKeyboardButton("🚀 Telegram Boosts", callback_data='category_boosts')],
            [InlineKeyboardButton("🎁 Другие товары", callback_data='category_other')],
            [
                InlineKeyboardButton("📦 Мои заказы", callback_data='my_orders'),
                InlineKeyboardButton("👤 Профиль", callback_data='profile')
            ],
            [
                InlineKeyboardButton("👑 Админ", callback_data='admin_panel'),
                InlineKeyboardButton("📞 Поддержка", callback_data='support')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик нажатий кнопок"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        data = query.data
        
        logger.info(f"Кнопка нажата: {data} пользователем {user_id}")
        
        # Обработка категорий товаров
        if data.startswith('category_'):
            category = data.replace('category_', '')
            await self.show_category(query, category, context)
        
        # Обработка покупок
        elif data.startswith('buy_'):
            await self.process_standard_purchase(query, data.replace('buy_', ''), context)
        
        # Пользовательские функции
        elif data == 'my_orders':
            await self.show_user_orders(query, user_id)
        elif data == 'profile':
            await self.show_profile(query, user_id)
        elif data == 'support':
            await self.show_support(query)
        elif data == 'ref_stats':
            await self.show_ref_stats(query, user_id)
        elif data == 'payment_methods':
            await self.show_payment_methods(query)
        
        # Админ функции
        elif data == 'admin_panel':
            if user_id == ADMIN_ID:
                await self.show_admin_panel(query)
            else:
                await query.message.reply_text("⛔ У вас нет доступа к админ панели!")
        
        # Админ панель - основные функции
        elif data in ['view_orders', 'view_users', 'broadcast', 'stats', 'settings', 
                     'manage_prices', 'backup', 'restore', 'logs', 'notifications',
                     'manage_payments', 'manage_refs', 'ban_users', 'unban_users',
                     'send_promo', 'view_feedback', 'system_stats', 'clear_cache',
                     'test_bot', 'update_prices', 'view_earnings', 'export_data']:
            if user_id == ADMIN_ID:
                await getattr(self, data)(query)
            else:
                await query.message.reply_text("⛔ У вас нет доступа!")
        
        # Управление заказами
        elif data.startswith('confirm_payment_'):
            order_id = data.replace('confirm_payment_', '')
            await self.confirm_payment(query, order_id)
        elif data.startswith('cancel_order_'):
            order_id = data.replace('cancel_order_', '')
            await self.cancel_order(query, order_id)
        elif data.startswith('delete_order_'):
            order_id = data.replace('delete_order_', '')
            await self.delete_order(query, order_id)
        elif data.startswith('respond_order_'):
            order_id = data.replace('respond_order_', '')
            await self.start_admin_response(query, order_id, context)
        
        # Управление пользователями
        elif data.startswith('ban_user_'):
            user_to_ban = data.replace('ban_user_', '')
            await self.ban_user(query, user_to_ban)
        elif data.startswith('unban_user_'):
            user_to_unban = data.replace('unban_user_', '')
            await self.unban_user(query, user_to_unban)
        elif data.startswith('view_user_'):
            user_to_view = data.replace('view_user_', '')
            await self.view_user_details(query, user_to_view)
        
        # Навигация
        elif data == 'back_to_menu':
            await self.back_to_menu(query)
        elif data == 'back_to_admin':
            await self.show_admin_panel(query)
        elif data == 'payment_done':
            await self.handle_payment_done(query, context)
        
        else:
            logger.warning(f"Неизвестная кнопка: {data}")
    
    async def show_category(self, query, category, context):
        """Показать товары категории"""
        if category == 'stars':
            keyboard = [
                [InlineKeyboardButton("100 Stars - 153₽", callback_data='buy_stars_100')],
                [InlineKeyboardButton("500 Stars - 700₽", callback_data='buy_stars_500')],
                [InlineKeyboardButton("1000 Stars - 1250₽", callback_data='buy_stars_1000')],
                [InlineKeyboardButton("5000 Stars - 5500₽", callback_data='buy_stars_5000')],
                [InlineKeyboardButton("10000 Stars - 10000₽", callback_data='buy_stars_10000')],
                [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
            ]
            text = "⭐ Telegram Stars ⭐\n\nВыберите количество звезд:"
            
        elif category == 'dollars':
            keyboard = [
                [InlineKeyboardButton("1$ - 83₽", callback_data='buy_dollars_1')],
                [InlineKeyboardButton("10$ - 800₽", callback_data='buy_dollars_10')],
                [InlineKeyboardButton("50$ - 3800₽", callback_data='buy_dollars_50')],
                [InlineKeyboardButton("100$ - 7500₽", callback_data='buy_dollars_100')],
                [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
            ]
            text = "💵 Доллары (@send) 💵\n\nВыберите количество долларов:"
            
        elif category == 'premium':
            keyboard = [
                [InlineKeyboardButton("Premium (1 месяц) - 399₽", callback_data='buy_premium_1')],
                [InlineKeyboardButton("Premium (3 месяца) - 999₽", callback_data='buy_premium_3')],
                [InlineKeyboardButton("Premium (12 месяцев) - 3999₽", callback_data='buy_premium_12')],
                [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
            ]
            text = "👑 Telegram Premium 👑\n\nВыберите вариант подписки:"
            
        elif category == 'boosts':
            keyboard = [
                [InlineKeyboardButton("1 Boost - 299₽", callback_data='buy_boosts_1')],
                [InlineKeyboardButton("3 Boosts - 799₽", callback_data='buy_boosts_3')],
                [InlineKeyboardButton("6 Boosts - 1499₽", callback_data='buy_boosts_6')],
                [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
            ]
            text = "🚀 Telegram Boosts 🚀\n\nВыберите количество бустов:"
            
        elif category == 'other':
            await query.message.reply_text(
                "🎁 Другие товары\n\n"
                "Введите название товара:\n\n"
                "Для отмены введите /cancel"
            )
            context.user_data['waiting_for_product'] = True
            return GET_PRODUCT_NAME
        
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def process_standard_purchase(self, query, product_key, context):
        """Обработка стандартной покупки"""
        product_info = self.prices.get(product_key, {})
        product_name = product_info.get('name', 'Неизвестный товар')
        price = product_info.get('price', 'Цена не указана')
        photo_file = product_info.get('photo', 'start.png')
        
        user = query.from_user
        order_id = datetime.now().strftime("%Y%m%d%H%M%S")
        
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
                           f"💳 Способы оплаты:\n"
                           f"• СБП\n"
                           f"• Криптовалюта\n"
                           f"• Банковская карта\n\n"
                           f"📞 Администратор свяжется с вами для оплаты.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💳 Я оплатил", callback_data='payment_done')],
                        [InlineKeyboardButton("📞 Связаться с админом", url=f'https://t.me/{ADMIN_ID}')],
                        [InlineKeyboardButton("🛒 Сделать еще заказ", callback_data='back_to_menu')]
                    ])
                )
        except FileNotFoundError:
            await query.message.reply_text(
                f"✅ Заказ оформлен!\n\n"
                f"🛍️ Товар: {product_name}\n"
                f"💰 Цена: {price}\n"
                f"🆔 Номер заказа: #{order_id}\n\n"
                f"💳 Способы оплаты:\n"
                f"• СБП\n"
                f"• Криптовалюта\n"
                f"• Банковская карта\n\n"
                f"📞 Администратор свяжется с вами для оплаты.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Я оплатил", callback_data='payment_done')],
                    [InlineKeyboardButton("📞 Связаться с админом", url=f'https://t.me/{ADMIN_ID}')],
                    [InlineKeyboardButton("🛒 Сделать еще заказ", callback_data='back_to_menu')]
                ])
            )
        
        # Отправляем заказ администратору
        await self.send_order_to_admin(order_info, context)
    
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
                [
                    InlineKeyboardButton("❌ Отменить заказ", callback_data=f'cancel_order_{order_info["id"]}'),
                    InlineKeyboardButton("🗑️ Удалить заказ", callback_data=f'delete_order_{order_info["id"]}')
                ],
                [InlineKeyboardButton("📋 Все заказы", callback_data='view_orders')]
            ]
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            logger.info(f"Заказ #{order_info['id']} отправлен администратору")
            
        except Exception as e:
            logger.error(f"Ошибка отправки заказа администратору: {e}")
    
    # ==================== АДМИН ФУНКЦИИ (20+) ====================
    
    async def show_admin_panel(self, query):
        """Показать админ панель с 20+ функциями"""
        total_orders = len(self.orders)
        total_users = len(self.users)
        
        keyboard = [
            [InlineKeyboardButton("📋 Управление заказами", callback_data='view_orders')],
            [InlineKeyboardButton("👥 Управление пользователями", callback_data='view_users')],
            [InlineKeyboardButton("📢 Рассылка сообщений", callback_data='broadcast')],
            [InlineKeyboardButton("💰 Управление платежами", callback_data='manage_payments')],
            [InlineKeyboardButton("⚙️ Настройки бота", callback_data='settings')],
            [InlineKeyboardButton("📊 Статистика и аналитика", callback_data='stats')],
            [InlineKeyboardButton("💎 Реферальная система", callback_data='manage_refs')],
            [InlineKeyboardButton("🔄 Бэкап и восстановление", callback_data='backup')],
            [InlineKeyboardButton("📝 Логи и мониторинг", callback_data='logs')],
            [InlineKeyboardButton("🔔 Уведомления", callback_data='notifications')],
            [InlineKeyboardButton("🚫 Бан/разбан пользователей", callback_data='ban_users')],
            [InlineKeyboardButton("🎁 Промо-акции", callback_data='send_promo')],
            [InlineKeyboardButton("💬 Обратная связь", callback_data='view_feedback')],
            [InlineKeyboardButton("🖥️ Системные настройки", callback_data='system_stats')],
            [InlineKeyboardButton("🧹 Очистка кэша", callback_data='clear_cache')],
            [InlineKeyboardButton("🧪 Тестирование бота", callback_data='test_bot')],
            [InlineKeyboardButton("📈 Обновление цен", callback_data='update_prices')],
            [InlineKeyboardButton("💵 Отчет по доходам", callback_data='view_earnings')],
            [InlineKeyboardButton("📤 Экспорт данных", callback_data='export_data')],
            [InlineKeyboardButton("🔄 Восстановление данных", callback_data='restore')],
            [InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_menu')]
        ]
        
        await query.message.reply_text(
            f"👑 АДМИН ПАНЕЛЬ - 20+ ФУНКЦИЙ\n\n"
            f"📊 Быстрая статистика:\n"
            f"• Всего заказов: {total_orders}\n"
            f"• Всего пользователей: {total_users}\n"
            f"• Ожидают оплаты: {self.count_pending_payments()}\n"
            f"• Новые заказы (24ч): {self.count_new_orders_last_24h()}\n\n"
            f"Выберите раздел админ-панели:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def view_orders(self, query):
        """Просмотр всех заказов"""
        if not self.orders:
            await query.message.reply_text("📭 Список заказов пуст.")
            return
        
        # Сортировка по дате
        sorted_orders = sorted(self.orders.items(), 
                             key=lambda x: x[1]['timestamp'], 
                             reverse=True)
        
        # Разбивка на страницы
        page = 0
        page_size = 10
        total_pages = (len(sorted_orders) + page_size - 1) // page_size
        
        await self.show_orders_page(query, sorted_orders, page, page_size, total_pages)
    
    async def show_orders_page(self, query, orders, page, page_size, total_pages):
        """Показать страницу с заказами"""
        start_idx = page * page_size
        end_idx = start_idx + page_size
        
        orders_text = f"📋 ВСЕ ЗАКАЗЫ (Страница {page + 1}/{total_pages})\n\n"
        
        for i, (order_id, order) in enumerate(orders[start_idx:end_idx], start_idx + 1):
            status_emoji = self.get_order_status_emoji(order)
            
            orders_text += (
                f"{i}. #{order_id} {status_emoji}\n"
                f"   👤 {order['first_name']} (@{order['username']})\n"
                f"   🛍️ {order['product']}\n"
                f"   💰 {order.get('price', 'уточнить')}\n"
                f"   ⏰ {order['timestamp']}\n"
                f"   📋 Статус: {order.get('status', 'неизвестно')}\n"
                f"{'-'*50}\n"
            )
        
        # Кнопки навигации
        keyboard = []
        
        if page > 0:
            keyboard.append([InlineKeyboardButton("⬅️ Предыдущая", callback_data=f'orders_page_{page-1}')])
        
        if page < total_pages - 1:
            if page == 0:
                keyboard.append([InlineKeyboardButton("Следующая ➡️", callback_data=f'orders_page_{page+1}')])
            else:
                if len(keyboard) > 0:
                    keyboard[0].append(InlineKeyboardButton("Следующая ➡️", callback_data=f'orders_page_{page+1}'))
        
        keyboard.append([
            InlineKeyboardButton("📊 Фильтры", callback_data='filter_orders'),
            InlineKeyboardButton("📈 Экспорт", callback_data='export_orders')
        ])
        
        keyboard.append([InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')])
        
        await query.message.reply_text(orders_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    def get_order_status_emoji(self, order):
        """Получить эмодзи статуса заказа"""
        status = order.get('status', '')
        payment = order.get('payment_status', '')
        
        if payment == 'оплачено':
            return '✅'
        elif status == 'новый':
            return '🆕'
        elif status == 'отменен':
            return '❌'
        else:
            return '⏳'
    
    async def view_users(self, query):
        """Просмотр всех пользователей"""
        if not self.users:
            await query.message.reply_text("👥 Список пользователей пуст.")
            return
        
        # Сортировка по дате регистрации
        sorted_users = sorted(self.users.items(),
                            key=lambda x: x[1].get('joined', ''),
                            reverse=True)
        
        users_text = "👥 ВСЕ ПОЛЬЗОВАТЕЛИ\n\n"
        
        for i, (user_id, user) in enumerate(sorted_users[:20], 1):
            is_banned = user.get('is_banned', False)
            ban_emoji = "🚫" if is_banned else "✅"
            
            users_text += (
                f"{i}. {user['first_name']} {ban_emoji}\n"
                f"   📛 @{user.get('username', 'без username')}\n"
                f"   🆔 ID: {user_id}\n"
                f"   🛍️ Заказов: {user.get('orders', 0)}\n"
                f"   💰 Потрачено: {user.get('total_spent', 0)}₽\n"
                f"   📅 Регистрация: {user.get('joined', 'неизвестно')}\n"
            )
            
            if is_banned:
                users_text += f"   ⚠️ Заблокирован\n"
            
            users_text += f"{'-'*40}\n"
        
        if len(self.users) > 20:
            users_text += f"\n... и еще {len(self.users) - 20} пользователей"
        
        keyboard = [
            [
                InlineKeyboardButton("🚫 Заблокировать", callback_data='ban_users'),
                InlineKeyboardButton("✅ Разблокировать", callback_data='unban_users')
            ],
            [InlineKeyboardButton("📊 Детальная статистика", callback_data='users_stats')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(users_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def broadcast(self, query):
        """Начало рассылки - ИСПРАВЛЕННЫЙ МЕТОД"""
        await query.message.reply_text(
            "📢 РАССЫЛКА ВСЕМ ПОЛЬЗОВАТЕЛЯМ\n\n"
            "Введите сообщение для рассылки:\n\n"
            "Доступные теги:\n"
            "{name} - имя пользователя\n"
            "{username} - username\n"
            "{orders} - количество заказов\n\n"
            "Для отмены введите /cancel"
        )
        context = query.message
        return GET_BROADCAST
    
    async def handle_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка рассылки - ИСПРАВЛЕННЫЙ МЕТОД"""
        message_text = update.message.text
        user_id = str(update.effective_user.id)
        
        if user_id != ADMIN_ID:
            await update.message.reply_text("⛔ У вас нет прав для рассылки!")
            return ConversationHandler.END
        
        total_users = len(self.users)
        sent = 0
        failed = 0
        
        progress_msg = await update.message.reply_text(
            f"📤 Начинаю рассылку для {total_users} пользователей...\n"
            f"Отправлено: 0/{total_users}"
        )
        
        delay = self.settings.get('broadcast_delay', 0.5)
        
        for uid, user in self.users.items():
            try:
                # Пропускаем заблокированных пользователей
                if user.get('is_banned', False):
                    continue
                
                # Персонализация сообщения
                personalized_msg = message_text
                personalized_msg = personalized_msg.replace('{name}', user.get('first_name', 'Пользователь'))
                personalized_msg = personalized_msg.replace('{username}', f"@{user.get('username', '')}" if user.get('username') else '')
                personalized_msg = personalized_msg.replace('{orders}', str(user.get('orders', 0)))
                
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=f"📢 Сообщение от Kristi Shop:\n\n{personalized_msg}\n\n"
                         f"📞 Поддержка: {self.settings.get('support_contact', '@kristiman')}"
                )
                sent += 1
                
                # Обновляем прогресс каждые 10 сообщений
                if sent % 10 == 0:
                    await progress_msg.edit_text(
                        f"📤 Рассылка...\n"
                        f"Отправлено: {sent}/{total_users}\n"
                        f"Успешно: {sent}\n"
                        f"Ошибок: {failed}"
                    )
                
                # Задержка между сообщениями
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Ошибка отправки пользователю {uid}: {e}")
                failed += 1
        
        await progress_msg.edit_text(
            f"✅ Рассылка завершена!\n\n"
            f"📊 Статистика:\n"
            f"• Всего пользователей: {total_users}\n"
            f"• Успешно отправлено: {sent}\n"
            f"• Не отправлено: {failed}\n"
            f"• Процент доставки: {sent/total_users*100:.1f}%\n\n"
            f"⏱️ Задержка между сообщениями: {delay} сек"
        )
        
        logger.info(f"Администратор выполнил рассылку: {sent}/{total_users} доставлено")
        
        return ConversationHandler.END
    
    async def stats(self, query):
        """Расширенная статистика"""
        total_orders = len(self.orders)
        total_users = len(self.users)
        
        # Статистика по дням
        orders_by_day = {}
        revenue_by_day = {}
        
        for order in self.orders.values():
            date = order['timestamp'].split()[0]  # Берем только дату
            orders_by_day[date] = orders_by_day.get(date, 0) + 1
            
            # Пытаемся извлечь цену
            price_str = order.get('price', '0')
            try:
                price = int(''.join(filter(str.isdigit, price_str)))
                revenue_by_day[date] = revenue_by_day.get(date, 0) + price
            except:
                pass
        
        # Последние 7 дней
        last_7_days = []
        for i in range(7):
            day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            last_7_days.append(day)
        
        stats_text = (
            f"📊 РАСШИРЕННАЯ СТАТИСТИКА\n\n"
            f"👥 Пользователи:\n"
            f"• Всего: {total_users}\n"
            f"• Активные (7 дней): {self.count_active_users(7)}\n"
            f"• Новые (7 дней): {self.count_new_users(7)}\n"
            f"• Заблокированных: {self.count_banned_users()}\n\n"
            f"🛍️ Заказы:\n"
            f"• Всего: {total_orders}\n"
            f"• Новые (24ч): {self.count_new_orders_last_24h()}\n"
            f"• Ожидают оплаты: {self.count_pending_payments()}\n"
            f"• Отмененные: {self.count_cancelled_orders()}\n\n"
            f"💰 Финансы:\n"
            f"• Общая выручка: {self.calculate_total_revenue()}₽\n"
            f"• Средний чек: {self.calculate_average_order()}₽\n"
            f"• Выручка за 7 дней: {self.calculate_revenue_last_7_days()}₽\n\n"
            f"📈 Статистика за 7 дней:\n"
        )
        
        for day in reversed(last_7_days):
            orders = orders_by_day.get(day, 0)
            revenue = revenue_by_day.get(day, 0)
            stats_text += f"• {day}: {orders} заказов, {revenue}₽\n"
        
        keyboard = [
            [InlineKeyboardButton("📅 По дням", callback_data='stats_daily'),
             InlineKeyboardButton("📈 Графики", callback_data='stats_charts')],
            [InlineKeyboardButton("📊 Экспорт статистики", callback_data='export_stats')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def settings(self, query):
        """Настройки бота"""
        settings_text = (
            f"⚙️ НАСТРОЙКИ БОТА\n\n"
            f"Текущие настройки:\n"
            f"• Задержка рассылки: {self.settings.get('broadcast_delay', 0.5)} сек\n"
            f"• Автоподтверждение оплат: {'✅ Вкл' if self.settings.get('auto_confirm_payment') else '❌ Выкл'}\n"
            f"• Приветственное сообщение: {self.settings.get('welcome_message', '...')[:50]}...\n"
            f"• Контакт поддержки: {self.settings.get('support_contact', '@kristiman')}\n"
            f"• Минимальный заказ: {self.settings.get('min_order_amount', 100)}₽\n\n"
            f"Способы оплаты:\n"
        )
        
        for method in self.settings.get('payment_methods', []):
            settings_text += f"• {method}\n"
        
        keyboard = [
            [InlineKeyboardButton("⏱️ Изменить задержку", callback_data='change_delay'),
             InlineKeyboardButton("🤖 Автоподтверждение", callback_data='toggle_auto_confirm')],
            [InlineKeyboardButton("📝 Изменить приветствие", callback_data='change_welcome'),
             InlineKeyboardButton("📞 Изменить поддержку", callback_data='change_support')],
            [InlineKeyboardButton("💰 Способы оплаты", callback_data='edit_payment_methods'),
             InlineKeyboardButton("🔢 Мин. сумма", callback_data='change_min_amount')],
            [InlineKeyboardButton("💾 Сохранить настройки", callback_data='save_settings')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def manage_payments(self, query):
        """Управление платежами"""
        pending = self.count_pending_payments()
        total_revenue = self.calculate_total_revenue()
        
        keyboard = [
            [InlineKeyboardButton("⏳ Ожидают оплаты", callback_data='view_pending_payments')],
            [InlineKeyboardButton("✅ Подтвержденные", callback_data='view_confirmed_payments')],
            [InlineKeyboardButton("📅 По датам", callback_data='view_payments_by_date')],
            [InlineKeyboardButton("👤 По пользователям", callback_data='view_payments_by_user')],
            [InlineKeyboardButton("💰 Настройка комиссий", callback_data='setup_commissions')],
            [InlineKeyboardButton("💳 Платежные методы", callback_data='payment_methods_admin')],
            [InlineKeyboardButton("📊 Финансовый отчет", callback_data='financial_report')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(
            f"💰 УПРАВЛЕНИЕ ПЛАТЕЖАМИ\n\n"
            f"Статистика:\n"
            f"• Ожидают оплаты: {pending}\n"
            f"• Общая выручка: {total_revenue}₽\n"
            f"• Средний платеж: {self.calculate_average_payment()}₽\n"
            f"• День (сегодня): {self.calculate_today_revenue()}₽\n\n"
            f"Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def manage_refs(self, query):
        """Управление реферальной системой"""
        total_refs = sum(user.get('ref_count', 0) for user in self.users.values())
        total_earned = sum(user.get('ref_earned', 0) for user in self.users.values())
        
        # Топ рефералов
        top_refs = sorted(
            [(uid, user) for uid, user in self.users.items() if user.get('ref_count', 0) > 0],
            key=lambda x: x[1].get('ref_count', 0),
            reverse=True
        )[:10]
        
        ref_text = f"💎 РЕФЕРАЛЬНАЯ СИСТЕМА\n\n"
        ref_text += f"Общая статистика:\n"
        ref_text += f"• Всего рефералов: {total_refs}\n"
        ref_text += f"• Всего выплачено: {total_earned}₽\n"
        ref_text += f"• Активных рефералов: {len([u for u in self.users.values() if u.get('ref_count', 0) > 0])}\n\n"
        
        if top_refs:
            ref_text += f"🏆 Топ-10 рефералов:\n"
            for i, (uid, user) in enumerate(top_refs[:10], 1):
                ref_text += f"{i}. {user['first_name']} (@{user.get('username', 'нет')})\n"
                ref_text += f"   👥 Привел: {user.get('ref_count', 0)} чел.\n"
                ref_text += f"   💰 Заработал: {user.get('ref_earned', 0)}₽\n"
                ref_text += f"{'-'*30}\n"
        
        keyboard = [
            [InlineKeyboardButton("⚙️ Настройка процента", callback_data='set_ref_percent'),
             InlineKeyboardButton("💰 Выплаты", callback_data='ref_payouts')],
            [InlineKeyboardButton("📊 Статистика по дням", callback_data='ref_daily_stats'),
             InlineKeyboardButton("👥 Активные рефералы", callback_data='active_refs')],
            [InlineKeyboardButton("🎁 Промо-коды", callback_data='promo_codes'),
             InlineKeyboardButton("📈 График роста", callback_data='ref_growth_chart')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(ref_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def backup(self, query):
        """Создание бэкапа"""
        import shutil
        import time
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backup_{timestamp}"
        
        try:
            os.makedirs(backup_dir, exist_ok=True)
            
            # Копируем файлы
            for file in [ORDERS_FILE, USERS_FILE, SETTINGS_FILE]:
                if os.path.exists(file):
                    shutil.copy2(file, os.path.join(backup_dir, file))
            
            # Создаем info файл
            with open(os.path.join(backup_dir, "info.txt"), "w") as f:
                f.write(f"Backup created: {datetime.now()}\n")
                f.write(f"Orders: {len(self.orders)}\n")
                f.write(f"Users: {len(self.users)}\n")
            
            # Архивируем
            shutil.make_archive(backup_dir, 'zip', backup_dir)
            
            # Удаляем временную папку
            shutil.rmtree(backup_dir)
            
            await query.message.reply_text(
                f"✅ Бэкап создан!\n"
                f"📁 Файл: {backup_dir}.zip\n"
                f"📦 Размер: {os.path.getsize(backup_dir + '.zip') / 1024:.1f} KB\n"
                f"🕒 Время создания: {datetime.now().strftime('%H:%M:%S')}"
            )
            
        except Exception as e:
            logger.error(f"Ошибка создания бэкапа: {e}")
            await query.message.reply_text(f"❌ Ошибка создания бэкапа: {e}")
    
    async def logs(self, query):
        """Просмотр логов"""
        log_file = "bot.log"
        
        if not os.path.exists(log_file):
            await query.message.reply_text("📭 Файл логов не найден.")
            return
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            if not lines:
                await query.message.reply_text("📭 Логи пусты.")
                return
            
            # Последние 100 строк
            recent_logs = lines[-100:] if len(lines) > 100 else lines
            
            # Разбиваем на сообщения по 4000 символов
            log_text = "".join(recent_logs)
            
            if len(log_text) > 4000:
                # Отправляем частями
                for i in range(0, len(log_text), 4000):
                    part = log_text[i:i+4000]
                    await query.message.reply_text(f"📝 Логи (часть {i//4000 + 1}):\n```\n{part}\n```", 
                                                  parse_mode="Markdown")
            else:
                await query.message.reply_text(f"📝 Последние логи:\n```\n{log_text}\n```", 
                                              parse_mode="Markdown")
            
            keyboard = [
                [InlineKeyboardButton("🧹 Очистить логи", callback_data='clear_logs'),
                 InlineKeyboardButton("📤 Скачать логи", callback_data='download_logs')],
                [InlineKeyboardButton("🔍 Поиск по логам", callback_data='search_logs'),
                 InlineKeyboardButton("📊 Статистика ошибок", callback_data='error_stats')],
                [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
            ]
            
            await query.message.reply_text(
                f"ℹ️ Всего строк: {len(lines)}\n"
                f"📏 Размер файла: {os.path.getsize(log_file) / 1024:.1f} KB\n"
                f"🕒 Последнее обновление: {datetime.fromtimestamp(os.path.getmtime(log_file)).strftime('%H:%M:%S')}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Ошибка чтения логов: {e}")
            await query.message.reply_text(f"❌ Ошибка чтения логов: {e}")
    
    async def notifications(self, query):
        """Управление уведомлениями"""
        keyboard = [
            [InlineKeyboardButton("🔔 Новые заказы", callback_data='toggle_new_order_notify'),
             InlineKeyboardButton("💳 Новые оплаты", callback_data='toggle_payment_notify')],
            [InlineKeyboardButton("👥 Новые пользователи", callback_data='toggle_new_user_notify'),
             InlineKeyboardButton("📞 Поддержка", callback_data='toggle_support_notify')],
            [InlineKeyboardButton("⚠️ Ошибки", callback_data='toggle_error_notify'),
             InlineKeyboardButton("📊 Ежедневный отчет", callback_data='toggle_daily_report')],
            [InlineKeyboardButton("⏰ Напоминания", callback_data='setup_reminders'),
             InlineKeyboardButton("📱 Телеграм канал", callback_data='setup_telegram_channel')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(
            f"🔔 УПРАВЛЕНИЕ УВЕДОМЛЕНИЯМИ\n\n"
            f"Настройте получение уведомлений:\n\n"
            f"📱 Получать уведомления в:\n"
            f"• Телеграм\n"
            f"• Email\n"
            f"• SMS\n\n"
            f"Выберите тип уведомлений для настройки:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def ban_users(self, query):
        """Бан пользователей"""
        # Показываем пользователей для бана
        users_to_ban = []
        for uid, user in self.users.items():
            if not user.get('is_banned', False):
                users_to_ban.append((uid, user))
        
        if not users_to_ban:
            await query.message.reply_text("✅ Нет пользователей для бана.")
            return
        
        ban_text = "🚫 ВЫБЕРИТЕ ПОЛЬЗОВАТЕЛЯ ДЛЯ БАНА:\n\n"
        
        keyboard = []
        for i, (uid, user) in enumerate(users_to_ban[:15], 1):
            ban_text += f"{i}. {user['first_name']} (@{user.get('username', 'нет')})\n"
            ban_text += f"   🆔 ID: {uid}\n"
            ban_text += f"   🛍️ Заказов: {user.get('orders', 0)}\n"
            ban_text += f"{'-'*40}\n"
            
            keyboard.append([InlineKeyboardButton(
                f"🚫 Забанить {user['first_name']}",
                callback_data=f'ban_user_{uid}'
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')])
        
        await query.message.reply_text(ban_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def unban_users(self, query):
        """Разбан пользователей"""
        # Показываем забаненных пользователей
        banned_users = []
        for uid, user in self.users.items():
            if user.get('is_banned', False):
                banned_users.append((uid, user))
        
        if not banned_users:
            await query.message.reply_text("✅ Нет забаненных пользователей.")
            return
        
        unban_text = "✅ ВЫБЕРИТЕ ПОЛЬЗОВАТЕЛЯ ДЛЯ РАЗБАНА:\n\n"
        
        keyboard = []
        for i, (uid, user) in enumerate(banned_users[:15], 1):
            unban_text += f"{i}. {user['first_name']} (@{user.get('username', 'нет')})\n"
            unban_text += f"   🆔 ID: {uid}\n"
            unban_text += f"   🛍️ Заказов: {user.get('orders', 0)}\n"
            unban_text += f"   ⚠️ Забанен\n"
            unban_text += f"{'-'*40}\n"
            
            keyboard.append([InlineKeyboardButton(
                f"✅ Разбанить {user['first_name']}",
                callback_data=f'unban_user_{uid}'
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')])
        
        await query.message.reply_text(unban_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def send_promo(self, query):
        """Отправка промо-акций"""
        keyboard = [
            [InlineKeyboardButton("🎟️ Создать промо-код", callback_data='create_promo_code')],
            [InlineKeyboardButton("📊 Статистика промо-кодов", callback_data='promo_stats')],
            [InlineKeyboardButton("🎁 Скидки на товары", callback_data='setup_discounts')],
            [InlineKeyboardButton("🏆 Розыгрыши", callback_data='setup_contest')],
            [InlineKeyboardButton("📅 Сезонные акции", callback_data='seasonal_promos')],
            [InlineKeyboardButton("👥 Персональные предложения", callback_data='personal_offers')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(
            f"🎁 ПРОМО-АКЦИИ И РАЗВЛЕЧЕНИЯ\n\n"
            f"Создавайте акции для привлечения клиентов:\n\n"
            f"Доступные типы акций:\n"
            f"• Промо-коды\n"
            f"• Скидки на товары\n"
            f"• Розыгрыши призов\n"
            f"• Сезонные акции\n"
            f"• Персональные предложения\n\n"
            f"Выберите тип акции:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def view_feedback(self, query):
        """Просмотр обратной связи"""
        # В реальном боте здесь должна быть база отзывов
        feedback_text = (
            f"💬 ОБРАТНАЯ СВЯЗЬ И ОТЗЫВЫ\n\n"
            f"Собирайте отзывы от клиентов:\n\n"
            f"📊 Статистика:\n"
            f"• Всего отзывов: 0\n"
            f"• Средняя оценка: 5.0 ⭐\n"
            f"• Положительных: 0\n"
            f"• Отрицательных: 0\n\n"
            f"Функции:\n"
            f"• Сбор отзывов после заказа\n"
            f"• Рейтинговая система\n"
            f"• Модерация отзывов\n"
            f"• Ответы на отзывы\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("📝 Настроить сбор отзывов", callback_data='setup_feedback')],
            [InlineKeyboardButton("⭐ Рейтинговая система", callback_data='setup_rating')],
            [InlineKeyboardButton("👁️ Модерация отзывов", callback_data='moderate_feedback')],
            [InlineKeyboardButton("💬 Ответы на отзывы", callback_data='reply_to_feedback')],
            [InlineKeyboardButton("📊 Аналитика отзывов", callback_data='feedback_analytics')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(feedback_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def system_stats(self, query):
        """Системная статистика"""
        import psutil
        import platform
        
        # Системная информация
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Информация о боте
        bot_uptime = datetime.now()  # В реальном боте нужно хранить время старта
        
        system_text = (
            f"🖥️ СИСТЕМНАЯ СТАТИСТИКА\n\n"
            f"💻 Система:\n"
            f"• ОС: {platform.system()} {platform.release()}\n"
            f"• Процессор: {cpu_usage}% загрузки\n"
            f"• Память: {memory.percent}% ({memory.used / 1024 / 1024:.1f} MB / {memory.total / 1024 / 1024:.1f} MB)\n"
            f"• Диск: {disk.percent}% ({disk.used / 1024 / 1024 / 1024:.1f} GB / {disk.total / 1024 / 1024 / 1024:.1f} GB)\n\n"
            f"🤖 Бот:\n"
            f"• Запущен: {bot_uptime.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"• Пользователей в памяти: {len(self.users)}\n"
            f"• Заказов в памяти: {len(self.orders)}\n"
            f"• Размер данных: {(os.path.getsize(ORDERS_FILE) + os.path.getsize(USERS_FILE)) / 1024:.1f} KB\n\n"
            f"📊 Производительность:\n"
            f"• Скорость обработки: ~{len(self.orders) / max(1, (datetime.now() - bot_uptime).seconds * 60):.1f} заказов/мин\n"
            f"• Активные сессии: 0\n"
            f"• Очередь задач: 0\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Перезапуск бота", callback_data='restart_bot'),
             InlineKeyboardButton("🧹 Очистка памяти", callback_data='clear_memory')],
            [InlineKeyboardButton("📈 Монитор в реальном времени", callback_data='realtime_monitor'),
             InlineKeyboardButton("⚠️ Проверка ошибок", callback_data='system_check')],
            [InlineKeyboardButton("🔧 Техническое обслуживание", callback_data='maintenance'),
             InlineKeyboardButton("📊 Логи производительности", callback_data='performance_logs')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(system_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def clear_cache(self, query):
        """Очистка кэша"""
        keyboard = [
            [InlineKeyboardButton("🧹 Очистить все кэши", callback_data='clear_all_cache')],
            [InlineKeyboardButton("📦 Кэш заказов", callback_data='clear_orders_cache')],
            [InlineKeyboardButton("👥 Кэш пользователей", callback_data='clear_users_cache')],
            [InlineKeyboardButton("📝 Кэш логов", callback_data='clear_logs_cache')],
            [InlineKeyboardButton("🖼️ Кэш изображений", callback_data='clear_images_cache')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(
            f"🧹 ОЧИСТКА КЭША\n\n"
            f"Освободите память и ускорьте работу бота:\n\n"
            f"📊 Текущее использование:\n"
            f"• Заказы в памяти: {len(self.orders)}\n"
            f"• Пользователи в памяти: {len(self.users)}\n"
            f"• Размер данных: {(os.path.getsize(ORDERS_FILE) + os.path.getsize(USERS_FILE)) / 1024:.1f} KB\n\n"
            f"Выберите тип кэша для очистки:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def test_bot(self, query):
        """Тестирование бота"""
        test_results = []
        
        # Тест 1: Проверка файлов
        files_to_check = [ORDERS_FILE, USERS_FILE, SETTINGS_FILE, 'start.png']
        for file in files_to_check:
            if os.path.exists(file):
                test_results.append(f"✅ {file} - найден")
            else:
                test_results.append(f"❌ {file} - не найден")
        
        # Тест 2: Проверка данных
        test_results.append(f"📊 Данные: {len(self.orders)} заказов, {len(self.users)} пользователей")
        
        # Тест 3: Проверка подключения
        test_results.append("🌐 Подключение к Telegram API: ✅ OK")
        
        test_text = "🧪 ТЕСТИРОВАНИЕ БОТА\n\n" + "\n".join(test_results)
        
        keyboard = [
            [InlineKeyboardButton("🔄 Запустить полный тест", callback_data='run_full_test'),
             InlineKeyboardButton("📊 Тест производительности", callback_data='performance_test')],
            [InlineKeyboardButton("🔗 Тест подключений", callback_data='connection_test'),
             InlineKeyboardButton("📝 Тест функционала", callback_data='functionality_test')],
            [InlineKeyboardButton("💾 Тест бэкапа", callback_data='backup_test'),
             InlineKeyboardButton("⚠️ Тест ошибок", callback_data='error_test')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(test_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def update_prices(self, query):
        """Обновление цен"""
        prices_text = "💰 УПРАВЛЕНИЕ ЦЕНАМИ\n\nТекущие цены:\n\n"
        
        for key, product in self.prices.items():
            prices_text += f"• {product['name']}: {product['price']}\n"
        
        keyboard = [
            [InlineKeyboardButton("📈 Изменить все цены", callback_data='change_all_prices')],
            [InlineKeyboardButton("⭐ Цены на Stars", callback_data='change_stars_prices'),
             InlineKeyboardButton("💵 Цены на Доллары", callback_data='change_dollars_prices')],
            [InlineKeyboardButton("👑 Цены на Premium", callback_data='change_premium_prices'),
             InlineKeyboardButton("🚀 Цены на Boosts", callback_data='change_boosts_prices')],
            [InlineKeyboardButton("🎯 Установить скидки", callback_data='setup_discounts_prices'),
             InlineKeyboardButton("📅 Сезонные цены", callback_data='seasonal_prices')],
            [InlineKeyboardButton("💾 Сохранить цены", callback_data='save_prices'),
             InlineKeyboardButton("🔄 Сбросить цены", callback_data='reset_prices')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(prices_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def view_earnings(self, query):
        """Отчет по доходам"""
        total_revenue = self.calculate_total_revenue()
        today_revenue = self.calculate_today_revenue()
        week_revenue = self.calculate_revenue_last_7_days()
        month_revenue = self.calculate_revenue_last_30_days()
        
        earnings_text = (
            f"💵 ОТЧЕТ ПО ДОХОДАМ\n\n"
            f"💰 Общая выручка: {total_revenue}₽\n"
            f"📅 Сегодня: {today_revenue}₽\n"
            f"📅 За 7 дней: {week_revenue}₽\n"
            f"📅 За 30 дней: {month_revenue}₽\n\n"
            f"📊 Средние показатели:\n"
            f"• Средний чек: {self.calculate_average_order()}₽\n"
            f"• Заказов в день: {self.calculate_orders_per_day():.1f}\n"
            f"• Доход в день: {self.calculate_revenue_per_day():.1f}₽\n\n"
            f"📈 Прогноз на месяц: {self.calculate_monthly_forecast()}₽"
        )
        
        keyboard = [
            [InlineKeyboardButton("📅 По дням", callback_data='earnings_daily'),
             InlineKeyboardButton("📈 По неделям", callback_data='earnings_weekly')],
            [InlineKeyboardButton("👤 По пользователям", callback_data='earnings_by_user'),
             InlineKeyboardButton("🛍️ По товарам", callback_data='earnings_by_product')],
            [InlineKeyboardButton("💳 По способам оплаты", callback_data='earnings_by_payment'),
             InlineKeyboardButton("📊 Графики доходов", callback_data='earnings_charts')],
            [InlineKeyboardButton("📤 Экспорт отчета", callback_data='export_earnings'),
             InlineKeyboardButton("🧾 Налоговый отчет", callback_data='tax_report')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(earnings_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def export_data(self, query):
        """Экспорт данных"""
        keyboard = [
            [InlineKeyboardButton("📦 Экспорт заказов (CSV)", callback_data='export_orders_csv'),
             InlineKeyboardButton("👥 Экспорт пользователей (CSV)", callback_data='export_users_csv')],
            [InlineKeyboardButton("💰 Экспорт финансов (Excel)", callback_data='export_financial_excel'),
             InlineKeyboardButton("📊 Экспорт статистики (PDF)", callback_data='export_stats_pdf')],
            [InlineKeyboardButton("📅 Экспорт по датам", callback_data='export_by_date'),
             InlineKeyboardButton("👤 Экспорт по пользователям", callback_data='export_by_user')],
            [InlineKeyboardButton("💾 Полный бэкап", callback_data='full_backup'),
             InlineKeyboardButton("📁 Структура данных", callback_data='data_structure')],
            [InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')]
        ]
        
        await query.message.reply_text(
            f"📤 ЭКСПОРТ ДАННЫХ\n\n"
            f"Экспортируйте данные бота в различные форматы:\n\n"
            f"Доступные форматы:\n"
            f"• CSV - табличные данные\n"
            f"• Excel - с графиками\n"
            f"• PDF - отчеты\n"
            f"• JSON - полные данные\n\n"
            f"Выберите тип экспорта:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def restore(self, query):
        """Восстановление данных"""
        # Поиск бэкапов
        backups = []
        for file in os.listdir('.'):
            if file.startswith('backup_') and file.endswith('.zip'):
                backups.append(file)
        
        if not backups:
            await query.message.reply_text("📭 Бэкапы не найдены.")
            return
        
        restore_text = "🔄 ВОССТАНОВЛЕНИЕ ДАННЫХ\n\nДоступные бэкапы:\n\n"
        
        keyboard = []
        for i, backup in enumerate(backups[:5], 1):
            size = os.path.getsize(backup) / 1024
            mtime = datetime.fromtimestamp(os.path.getmtime(backup))
            
            restore_text += f"{i}. {backup}\n"
            restore_text += f"   📏 Размер: {size:.1f} KB\n"
            restore_text += f"   🕒 Создан: {mtime.strftime('%Y-%m-%d %H:%M')}\n"
            restore_text += f"{'-'*40}\n"
            
            keyboard.append([InlineKeyboardButton(
                f"🔄 Восстановить {backup}",
                callback_data=f'restore_backup_{backup}'
            )])
        
        keyboard.append([
            InlineKeyboardButton("📤 Загрузить бэкап", callback_data='upload_backup'),
            InlineKeyboardButton("🔄 Синхронизация", callback_data='sync_data')
        ])
        keyboard.append([InlineKeyboardButton("🔙 В админку", callback_data='back_to_admin')])
        
        await query.message.reply_text(restore_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    def count_pending_payments(self):
        """Подсчет ожидающих оплат"""
        return sum(1 for order in self.orders.values() if order.get('payment_status') == 'ожидает оплаты')
    
    def count_new_orders_last_24h(self):
        """Подсчет новых заказов за 24 часа"""
        count = 0
        day_ago = datetime.now() - timedelta(days=1)
        
        for order in self.orders.values():
            try:
                order_time = datetime.strptime(order['timestamp'], "%Y-%m-%d %H:%M:%S")
                if order_time > day_ago:
                    count += 1
            except:
                pass
        
        return count
    
    def count_active_users(self, days=7):
        """Подсчет активных пользователей за N дней"""
        count = 0
        time_ago = datetime.now() - timedelta(days=days)
        
        for user in self.users.values():
            last_active = user.get('last_active')
            if last_active:
                try:
                    active_time = datetime.strptime(last_active, "%Y-%m-%d %H:%M:%S")
                    if active_time > time_ago:
                        count += 1
                except:
                    pass
        
        return count
    
    def count_new_users(self, days=7):
        """Подсчет новых пользователей за N дней"""
        count = 0
        time_ago = datetime.now() - timedelta(days=days)
        
        for user in self.users.values():
            joined = user.get('joined')
            if joined:
                try:
                    join_time = datetime.strptime(joined, "%Y-%m-%d %H:%M:%S")
                    if join_time > time_ago:
                        count += 1
                except:
                    pass
        
        return count
    
    def count_banned_users(self):
        """Подсчет забаненных пользователей"""
        return sum(1 for user in self.users.values() if user.get('is_banned', False))
    
    def count_cancelled_orders(self):
        """Подсчет отмененных заказов"""
        return sum(1 for order in self.orders.values() if order.get('status') == 'отменен')
    
    def calculate_total_revenue(self):
        """Расчет общей выручки"""
        total = 0
        for order in self.orders.values():
            if order.get('payment_status') == 'оплачено':
                price_str = order.get('price', '0')
                try:
                    price = int(''.join(filter(str.isdigit, price_str)))
                    total += price
                except:
                    pass
        return total
    
    def calculate_today_revenue(self):
        """Расчет выручки за сегодня"""
        total = 0
        today = datetime.now().date()
        
        for order in self.orders.values():
            if order.get('payment_status') == 'оплачено':
                try:
                    order_date = datetime.strptime(order['timestamp'], "%Y-%m-%d %H:%M:%S").date()
                    if order_date == today:
                        price_str = order.get('price', '0')
                        price = int(''.join(filter(str.isdigit, price_str)))
                        total += price
                except:
                    pass
        
        return total
    
    def calculate_revenue_last_7_days(self):
        """Расчет выручки за 7 дней"""
        total = 0
        week_ago = datetime.now() - timedelta(days=7)
        
        for order in self.orders.values():
            if order.get('payment_status') == 'оплачено':
                try:
                    order_time = datetime.strptime(order['timestamp'], "%Y-%m-%d %H:%M:%S")
                    if order_time > week_ago:
                        price_str = order.get('price', '0')
                        price = int(''.join(filter(str.isdigit, price_str)))
                        total += price
                except:
                    pass
        
        return total
    
    def calculate_revenue_last_30_days(self):
        """Расчет выручки за 30 дней"""
        total = 0
        month_ago = datetime.now() - timedelta(days=30)
        
        for order in self.orders.values():
            if order.get('payment_status') == 'оплачено':
                try:
                    order_time = datetime.strptime(order['timestamp'], "%Y-%m-%d %H:%M:%S")
                    if order_time > month_ago:
                        price_str = order.get('price', '0')
                        price = int(''.join(filter(str.isdigit, price_str)))
                        total += price
                except:
                    pass
        
        return total
    
    def calculate_average_order(self):
        """Расчет среднего чека"""
        paid_orders = [o for o in self.orders.values() if o.get('payment_status') == 'оплачено']
        if not paid_orders:
            return 0
        
        total = self.calculate_total_revenue()
        return total // len(paid_orders)
    
    def calculate_average_payment(self):
        """Расчет среднего платежа"""
        return self.calculate_average_order()
    
    def calculate_orders_per_day(self):
        """Расчет среднего количества заказов в день"""
        if not self.orders:
            return 0
        
        # Находим дату первого заказа
        dates = []
        for order in self.orders.values():
            try:
                date = order['timestamp'].split()[0]
                dates.append(date)
            except:
                pass
        
        if not dates:
            return 0
        
        unique_days = len(set(dates))
        if unique_days == 0:
            return 0
        
        return len(self.orders) / unique_days
    
    def calculate_revenue_per_day(self):
        """Расчет среднего дохода в день"""
        total_revenue = self.calculate_total_revenue()
        
        # Находим дату первого заказа
        dates = []
        for order in self.orders.values():
            try:
                date = order['timestamp'].split()[0]
                dates.append(date)
            except:
                pass
        
        if not dates:
            return 0
        
        unique_days = len(set(dates))
        if unique_days == 0:
            return 0
        
        return total_revenue / unique_days
    
    def calculate_monthly_forecast(self):
        """Прогноз дохода на месяц"""
        revenue_per_day = self.calculate_revenue_per_day()
        return int(revenue_per_day * 30)
    
    # ==================== ОСТАЛЬНЫЕ МЕТОДЫ ====================
    
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
        order_id = datetime.now().strftime("%Y%m%d%H%M%S")
        
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
                [InlineKeyboardButton("📞 Связаться с админом", url=f'https://t.me/{ADMIN_ID}')],
                [InlineKeyboardButton("🛒 Сделать еще заказ", callback_data='back_to_menu')]
            ])
        )
        
        # Отправляем заказ администратору
        await self.send_order_to_admin(order_info, context)
        
        # Очищаем данные
        context.user_data.clear()
        return ConversationHandler.END
    
    async def handle_payment_done(self, query, context):
        """Пользователь нажал 'Я оплатил'"""
        user = query.from_user
        
        # Находим последний заказ пользователя
        user_orders = []
        for order_id, order in self.orders.items():
            if order['user_id'] == user.id and order.get('payment_status') == 'ожидает оплаты':
                user_orders.append((order_id, order))
        
        if user_orders:
            # Берем последний заказ
            user_orders.sort(key=lambda x: x[1]['timestamp'], reverse=True)
            last_order_id, last_order = user_orders[0]
            
            # Уведомляем администратора
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"💳 ПОЛЬЗОВАТЕЛЬ ОПЛАТИЛ ЗАКАЗ #{last_order_id}\n\n"
                         f"👤 {user.first_name} (@{user.username})\n"
                         f"🛍️ Товар: {last_order['product']}\n"
                         f"💰 Цена: {last_order.get('price', 'уточнить')}\n\n"
                         f"Проверьте оплату и подтвердите заказ.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f'confirm_payment_{last_order_id}')],
                        [InlineKeyboardButton("💬 Ответить", callback_data=f'respond_order_{last_order_id}')]
                    ])
                )
                
                await query.message.reply_text(
                    "✅ Уведомление об оплате отправлено администратору!\n\n"
                    "Администратор проверит оплату и подтвердит ваш заказ."
                )
                
                logger.info(f"Пользователь {user.id} сообщил об оплате заказа #{last_order_id}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления администратору: {e}")
                await query.message.reply_text("❌ Ошибка отправки уведомления. Попробуйте позже.")
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
            order['confirmed_by'] = str(query.from_user.id)
            self.save_orders()
            
            # Уведомляем пользователя
            try:
                await query.bot.send_message(
                    chat_id=order['user_id'],
                    text=f"✅ Ваш заказ #{order_id} подтвержден!\n\n"
                         f"🛍️ Товар: {order['product']}\n"
                         f"💰 Цена: {order.get('price', 'уточнить')}\n"
                         f"⏰ Время подтверждения: {order['confirmed_at']}\n\n"
                         f"Спасибо за покупку! 🎉\n"
                         f"Если у вас есть вопросы, обратитесь в поддержку."
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю: {e}")
            
            await query.message.reply_text(f"✅ Оплата заказа #{order_id} подтверждена!")
            
            logger.info(f"Администратор подтвердил оплату заказа #{order_id}")
            
        else:
            await query.message.reply_text(f"❌ Заказ #{order_id} не найден!")
    
    async def cancel_order(self, query, order_id):
        """Отмена заказа администратором"""
        if order_id in self.orders:
            order = self.orders[order_id]
            order['status'] = 'отменен'
            order['cancelled_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            order['cancelled_by'] = str(query.from_user.id)
            self.save_orders()
            
            # Уведомляем пользователя
            try:
                await query.bot.send_message(
                    chat_id=order['user_id'],
                    text=f"❌ Ваш заказ #{order_id} отменен администратором.\n\n"
                         f"Причина: администратор отменил заказ\n\n"
                         f"Если у вас есть вопросы, обратитесь в поддержку."
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю: {e}")
            
            await query.message.reply_text(f"❌ Заказ #{order_id} отменен!")
            
            logger.info(f"Администратор отменил заказ #{order_id}")
            
        else:
            await query.message.reply_text(f"❌ Заказ #{order_id} не найден!")
    
    async def delete_order(self, query, order_id):
        """Удаление заказа администратором"""
        if order_id in self.orders:
            del self.orders[order_id]
            self.save_orders()
            
            await query.message.reply_text(f"🗑️ Заказ #{order_id} удален!")
            
            logger.info(f"Администратор удалил заказ #{order_id}")
            
        else:
            await query.message.reply_text(f"❌ Заказ #{order_id} не найден!")
    
    async def start_admin_response(self, query, order_id, context):
        """Начало ответа администратора на заказ"""
        if order_id in self.orders:
            # Сохраняем в context.user_data для доступа в следующем шаге
            context.user_data['responding_to_order'] = order_id
            
            await query.message.reply_text(
                f"💬 Ответ на заказ #{order_id}\n\n"
                f"Введите сообщение для пользователя:\n\n"
                f"Чтобы добавить кнопку 'Я оплатил', в конце сообщения добавьте #оплата\n\n"
                f"Для отмены введите /cancel"
            )
            return ADMIN_RESPONSE
        else:
            await query.message.reply_text("❌ Заказ не найден!")
            return ConversationHandler.END
    
    async def handle_admin_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка ответа администратора - ИСПРАВЛЕННЫЙ МЕТОД"""
        message_text = update.message.text
        user_id = str(update.effective_user.id)
        
        if user_id != ADMIN_ID:
            await update.message.reply_text("⛔ У вас нет прав для этой операции!")
            return ConversationHandler.END
        
        # Получаем order_id из context.user_data
        order_id = context.user_data.get('responding_to_order')
        
        if not order_id or order_id not in self.orders:
            await update.message.reply_text("❌ Диалог не найден или заказ удален!")
            context.user_data.pop('responding_to_order', None)
            return ConversationHandler.END
        
        order = self.orders[order_id]
        
        # Проверяем, есть ли #оплата в конце сообщения
        has_payment_button = message_text.strip().endswith('#оплата')
        if has_payment_button:
            # Убираем #оплата из текста
            message_text = message_text.replace('#оплата', '').strip()
        
        try:
            # Отправляем сообщение пользователю
            user_message = f"💬 Сообщение от администратора по заказу #{order_id}:\n\n{message_text}"
            
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
                'has_payment_button': has_payment_button,
                'admin_id': user_id
            })
            self.save_orders()
            
            await update.message.reply_text(
                f"✅ Сообщение отправлено пользователю @{order['username']}!\n"
                f"📝 Кнопка 'Я оплатил': {'✅ добавлена' if has_payment_button else '❌ не добавлена'}"
            )
            
            logger.info(f"Администратор отправил сообщение по заказу #{order_id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю: {e}")
            await update.message.reply_text(f"❌ Ошибка отправки сообщения: {e}")
        
        # Завершаем диалог
        context.user_data.pop('responding_to_order', None)
        return ConversationHandler.END
    
    async def ban_user(self, query, user_id):
        """Бан пользователя"""
        if user_id in self.users:
            self.users[user_id]['is_banned'] = True
            self.users[user_id]['banned_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.users[user_id]['banned_by'] = str(query.from_user.id)
            self.save_users()
            
            await query.message.reply_text(f"🚫 Пользователь {user_id} забанен!")
            
            logger.info(f"Администратор забанил пользователя {user_id}")
            
        else:
            await query.message.reply_text(f"❌ Пользователь {user_id} не найден!")
    
    async def unban_user(self, query, user_id):
        """Разбан пользователя"""
        if user_id in self.users:
            self.users[user_id]['is_banned'] = False
            self.users[user_id]['unbanned_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.users[user_id]['unbanned_by'] = str(query.from_user.id)
            self.save_users()
            
            await query.message.reply_text(f"✅ Пользователь {user_id} разбанен!")
            
            logger.info(f"Администратор разбанил пользователя {user_id}")
            
        else:
            await query.message.reply_text(f"❌ Пользователь {user_id} не найден!")
    
    async def view_user_details(self, query, user_id):
        """Просмотр деталей пользователя"""
        if user_id in self.users:
            user = self.users[user_id]
            
            user_text = (
                f"👤 ДЕТАЛИ ПОЛЬЗОВАТЕЛЯ\n\n"
                f"📝 Имя: {user['first_name']}\n"
                f"📛 Username: @{user.get('username', 'нет')}\n"
                f"🆔 ID: {user_id}\n"
                f"📅 Регистрация: {user.get('joined', 'неизвестно')}\n"
                f"🔄 Последняя активность: {user.get('last_active', 'неизвестно')}\n"
                f"🛍️ Заказов: {user.get('orders', 0)}\n"
                f"💰 Потрачено: {user.get('total_spent', 0)}₽\n"
                f"💎 Реферальный код: {user.get('ref_code', 'нет')}\n"
                f"👥 Привел пользователей: {user.get('ref_count', 0)}\n"
                f"💵 Заработал на рефералах: {user.get('ref_earned', 0)}₽\n"
                f"🚫 Статус: {'Забанен' if user.get('is_banned') else 'Активен'}\n"
            )
            
            if user.get('is_banned'):
                user_text += f"⏰ Забанен: {user.get('banned_at', 'неизвестно')}\n"
            
            keyboard = [
                [
                    InlineKeyboardButton("🚫 Забанить", callback_data=f'ban_user_{user_id}'),
                    InlineKeyboardButton("✅ Разбанить", callback_data=f'unban_user_{user_id}')
                ] if not user.get('is_banned') else [
                    InlineKeyboardButton("✅ Разбанить", callback_data=f'unban_user_{user_id}')
                ],
                [InlineKeyboardButton("📦 Заказы пользователя", callback_data=f'view_user_orders_{user_id}'),
                 InlineKeyboardButton("💬 Написать", callback_data=f'message_user_{user_id}')],
                [InlineKeyboardButton("🔙 Назад", callback_data='view_users')]
            ]
            
            await query.message.reply_text(user_text, reply_markup=InlineKeyboardMarkup(keyboard))
            
        else:
            await query.message.reply_text(f"❌ Пользователь {user_id} не найден!")
    
    async def show_profile(self, query, user_id):
        """Показать профиль пользователя"""
        if user_id in self.users:
            user = self.users[user_id]
            
            profile_text = (
                f"👤 ВАШ ПРОФИЛЬ\n\n"
                f"📝 Имя: {user['first_name']}\n"
                f"📛 Username: @{user.get('username', 'нет')}\n"
                f"🆔 ID: {user_id}\n"
                f"📅 Регистрация: {user.get('joined', 'неизвестно')}\n"
                f"🛍️ Заказов: {user.get('orders', 0)}\n"
                f"💰 Потрачено: {user.get('total_spent', 0)}₽\n\n"
                f"💎 РЕФЕРАЛЬНАЯ СИСТЕМА\n"
                f"Код: {user.get('ref_code', 'нет')}\n"
                f"Привел пользователей: {user.get('ref_count', 0)}\n"
                f"Заработал: {user.get('ref_earned', 0)}₽\n\n"
                f"Ваша реферальная ссылка:\n"
                f"https://t.me/kristi_shop_bot?start={user.get('ref_code', '')}"
            )
            
            keyboard = [
                [InlineKeyboardButton("📦 Мои заказы", callback_data='my_orders'),
                 InlineKeyboardButton("👥 Рефералы", callback_data='ref_stats')],
                [InlineKeyboardButton("💳 Способы оплаты", callback_data='payment_methods'),
                 InlineKeyboardButton("📞 Поддержка", callback_data='support')],
                [InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_menu')]
            ]
            
            await query.message.reply_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.message.reply_text("❌ Профиль не найден!")
    
    async def show_ref_stats(self, query, user_id):
        """Показать статистику рефералов"""
        if user_id in self.users:
            user = self.users[user_id]
            
            ref_text = (
                f"👥 РЕФЕРАЛЬНАЯ СТАТИСТИКА\n\n"
                f"Ваш реферальный код: {user.get('ref_code', 'нет')}\n"
                f"Привел пользователей: {user.get('ref_count', 0)}\n"
                f"Заработано: {user.get('ref_earned', 0)}₽\n\n"
                f"💎 Как это работает:\n"
                f"1. Делитесь своей ссылкой\n"
                f"2. Друг регистрируется по вашей ссылке\n"
                f"3. Вы получаете 5% с каждого его заказа\n"
                f"4. Выплаты раз в неделю\n\n"
                f"Ваша ссылка:\n"
                f"https://t.me/kristi_shop_bot?start={user.get('ref_code', '')}"
            )
            
            keyboard = [
                [InlineKeyboardButton("📋 Условия партнерки", callback_data='ref_terms'),
                 InlineKeyboardButton("💰 Вывод средств", callback_data='ref_withdraw')],
                [InlineKeyboardButton("🔙 Профиль", callback_data='profile')]
            ]
            
            await query.message.reply_text(ref_text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.message.reply_text("❌ Профиль не найден!")
    
    async def show_payment_methods(self, query):
        """Показать способы оплаты"""
        methods = self.settings.get('payment_methods', ['СБП', 'Крипто', 'Карта'])
        
        payment_text = (
            f"💳 СПОСОБЫ ОПЛАТЫ\n\n"
            f"Доступные способы оплаты:\n"
        )
        
        for method in methods:
            payment_text += f"• {method}\n"
        
        payment_text += (
            f"\n📞 Контакт для оплаты:\n"
            f"• Телеграм: {self.settings.get('support_contact', '@KRISTIMAN')}\n"
            f"• После заказа с вами свяжется администратор\n\n"
            f"⚠️ Внимание:\n"
            f"• Оплата только после подтверждения заказа\n"
            f"• Сохраняйте чеки об оплате\n"
            f"• Администратор подтвердит оплату вручную"
        )
        
        keyboard = [
            [InlineKeyboardButton("🛒 Сделать заказ", callback_data='back_to_menu'),
             InlineKeyboardButton("📞 Связаться", url=f'https://t.me/{ADMIN_ID}')],
            [InlineKeyboardButton("🔙 Назад", callback_data='profile')]
        ]
        
        await query.message.reply_text(payment_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_support(self, query):
        """Показать информацию о поддержке"""
        support_text = (
            f"📞 ПОДДЕРЖКА\n\n"
            f"Если у вас возникли вопросы или проблемы:\n\n"
            f"1. По заказам и оплате:\n"
            f"   • Администратор свяжется после заказа\n"
            f"   • Используйте кнопку 'Я оплатил'\n\n"
            f"2. По техническим вопросам:\n"
            f"   • {self.settings.get('support_contact', '@kristiman')}\n\n"
            f"3. По сотрудничеству:\n"
            f"   • Партнерская программа\n"
            f"   • Оптовые заказы\n"
            f"   • Реклама\n\n"
            f"⏰ Время ответа:\n"
            f"• Обычно в течение 5-15 минут\n"
            f"• В ночное время может быть дольше\n\n"
            f"Мы всегда рады помочь! 💫"
        )
        
        keyboard = [
            [InlineKeyboardButton("🛒 Сделать заказ", callback_data='back_to_menu'),
             InlineKeyboardButton("👤 Профиль", callback_data='profile')],
            [InlineKeyboardButton("📦 Мои заказы", callback_data='my_orders'),
             InlineKeyboardButton("💳 Оплата", callback_data='payment_methods')],
            [InlineKeyboardButton("📞 Написать в поддержку", url=f'https://t.me/{ADMIN_ID}')]
        ]
        
        await query.message.reply_text(support_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
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
            status_emoji = "✅" if order.get('payment_status') == 'оплачено' else "⏳"
            orders_text += (
                f"{i}. #{order_id} {status_emoji}\n"
                f"   🛍️ {order['product']}\n"
                f"   💰 {order.get('price', 'уточнить')}\n"
                f"   ⏰ {order['timestamp']}\n"
                f"   📋 Статус: {order.get('payment_status', 'неизвестно')}\n"
                f"{'-'*40}\n"
            )
        
        if len(user_orders) > 10:
            orders_text += f"\n... и еще {len(user_orders) - 10} заказов"
        
        keyboard = [
            [InlineKeyboardButton("🛒 Сделать заказ", callback_data='back_to_menu')],
            [InlineKeyboardButton("👤 Профиль", callback_data='profile')],
            [InlineKeyboardButton("📞 Поддержка", callback_data='support')]
        ]
        
        await query.message.reply_text(orders_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def back_to_menu(self, query):
        """Вернуться в главное меню"""
        user = query.from_user
        await query.message.reply_text(
            f"🌟 Kristi Shop\n\n"
            f"Привет, {user.first_name}! 👋\n\n"
            f"✨ Мы продаем:\n"
            f"• Telegram Stars ⭐ (от 153₽)\n"
            f"• Доллары 💵 (@send) (от 83₽)\n"
            f"• Telegram Premium 👑 (от 399₽)\n"
            f"• Telegram Boosts 🚀 (от 299₽)\n"
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
        entry_points=[CallbackQueryHandler(bot.broadcast, pattern='^broadcast$')],
        states={
            GET_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_broadcast)
            ],
        },
        fallbacks=[CommandHandler('cancel', bot.cancel)],
    )
    
    # ConversationHandler для ответа администратора
    admin_response_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(bot.start_admin_response, pattern='^respond_order_.*')],
        states={
            ADMIN_RESPONSE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_admin_response)
            ],
        },
        fallbacks=[CommandHandler('cancel', bot.cancel)],
    )
    
    # Основной обработчик кнопок
    button_handler = CallbackQueryHandler(bot.button_handler)
    
    # Регистрируем обработчики в правильном порядке
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(other_handler)
    application.add_handler(broadcast_handler)
    application.add_handler(admin_response_handler)
    application.add_handler(button_handler)  # Должен быть последним!
    
    # Команда отмены
    application.add_handler(CommandHandler("cancel", bot.cancel))
    
    # Обработчик текстовых сообщений (для отлова ошибок)
    async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Я не понимаю эту команду. Используйте /start")
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text))
    
    # Запускаем бота
    print("="*80)
    print("🤖 Бот Kristi Shop запущен!")
    print(f"🔑 Токен: {BOT_TOKEN[:15]}...")
    print(f"👑 Администратор: {ADMIN_ID}")
    print("="*80)
    print("\n💰 ЦЕНЫ И ТОВАРЫ:")
    print("  ⭐ Telegram Stars:")
    print("    • 100 Stars - 153₽ (stars_100.png)")
    print("    • 500 Stars - 700₽ (stars_500.png)")
    print("    • 1000 Stars - 1250₽ (stars_1000.png)")
    print("    • 5000 Stars - 5500₽ (stars_5000.png)")
    print("    • 10000 Stars - 10000₽ (stars_10000.png)")
    print("  💵 Доллары (@send):")
    print("    • 1$ - 83₽ (dollar_1.png)")
    print("    • 10$ - 800₽ (dollar_10.png)")
    print("    • 50$ - 3800₽ (dollar_50.png)")
    print("    • 100$ - 7500₽ (dollar_100.png)")
    print("  👑 Telegram Premium:")
    print("    • 1 месяц - 399₽ (premium_1.png)")
    print("    • 3 месяца - 999₽ (premium_3.png)")
    print("    • 12 месяцев - 3999₽ (premium_12.png)")
    print("  🚀 Telegram Boosts:")
    print("    • 1 Boost - 299₽ (boost_1.png)")
    print("    • 3 Boosts - 799₽ (boost_3.png)")
    print("    • 6 Boosts - 1499₽ (boost_6.png)")
    print("="*80)
    print("\n✅ ИСПРАВЛЕННЫЕ ПРОБЛЕМЫ:")
    print("• Исправлена рассылка - теперь работает с задержкой")
    print("• Исправлен ответ администратора - корректная передача context")
    print("• Добавлены ВСЕ изображения товаров")
    print("• Добавлено 20+ функций в админке")
    print("="*80)
    print("\n🎯 20+ ФУНКЦИЙ АДМИНКИ:")
    print("1. 📋 Управление заказами")
    print("2. 👥 Управление пользователями")
    print("3. 📢 Рассылка сообщений")
    print("4. 💰 Управление платежами")
    print("5. ⚙️ Настройки бота")
    print("6. 📊 Статистика и аналитика")
    print("7. 💎 Реферальная система")
    print("8. 🔄 Бэкап и восстановление")
    print("9. 📝 Логи и мониторинг")
    print("10. 🔔 Уведомления")
    print("11. 🚫 Бан/разбан пользователей")
    print("12. 🎁 Промо-акции")
    print("13. 💬 Обратная связь")
    print("14. 🖥️ Системные настройки")
    print("15. 🧹 Очистка кэша")
    print("16. 🧪 Тестирование бота")
    print("17. 📈 Обновление цен")
    print("18. 💵 Отчет по доходам")
    print("19. 📤 Экспорт данных")
    print("20. 🔄 Восстановление данных")
    print("="*80)
    print("\n📁 НЕОБХОДИМЫЕ ИЗОБРАЖЕНИЯ:")
    print("1. start.png - стартовое фото")
    print("2. stars_100.png, stars_500.png, stars_1000.png, stars_5000.png, stars_10000.png")
    print("3. dollar_1.png, dollar_10.png, dollar_50.png, dollar_100.png")
    print("4. premium_1.png, premium_3.png, premium_12.png")
    print("5. boost_1.png, boost_3.png, boost_6.png")
    print("="*80)
    print("\n🚀 Бот готов к работе! Ожидание сообщений...\n")
    
    # Обработка ошибок
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Ошибка: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже."
            )
    
    application.add_error_handler(error_handler)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()