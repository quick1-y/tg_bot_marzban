# presentation/handlers/user_handlers.py
import logging
from typing import Optional
from aiogram import F
from aiogram.types import (
    Message,
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from presentation.handlers.base import BaseHandler
from presentation.keyboards.user_keyboards import get_user_main_keyboard
from presentation.keyboards.support_keyboards import (
    get_user_support_menu_keyboard,
    get_user_tickets_list_keyboard,
)
from domain.services.subscription_service import SubscriptionService
from domain.services.user_service import UserService
from domain.services.support_service import SupportService
from domain.models.subscription import SubscriptionResult
from core.config import config
import datetime


logger = logging.getLogger(__name__)


# === helpers ===
def build_welcome_message(support_text: str) -> str:
    return (
        "🔒 Добро пожаловать в VPN сервис!\n\n"
        "💎 Выберите удобный тип подписки:\n\n"
        f"• 📅 Ежемесячная — {config.STAR_PRICE_PER_MONTH}⭐/мес\n"
        f"• 💾 По трафику — {config.STAR_PRICE_PER_GB}⭐/ГБ\n\n"
        f"{support_text}"
    )


# === FSM состояния ===
class PurchaseStates(StatesGroup):
    choosing_plan_type = State()
    choosing_months = State()
    choosing_traffic = State()

class SupportStates(StatesGroup):
    waiting_for_message = State()
    viewing_tickets = State()
    viewing_ticket_detail = State()

# === helper ===
def detect_subscription_type(subscription_info) -> Optional[str]:
    if not subscription_info:
        return None
    for attr in ("data_limit_gb", "data_limit"):
        val = getattr(subscription_info, attr, None)
        if val:
            try:
                if isinstance(val, (int, float)) and val > 0:
                    return "traffic"
            except Exception:
                pass
    stype = getattr(subscription_info, "subscription_type", "") or ""
    st_lower = str(stype).lower()
    if "месяц" in st_lower or "monthly" in st_lower:
        return "monthly"
    if "гб" in st_lower or "gb" in st_lower or "трафик" in st_lower:
        return "traffic"
    return None


class UserHandlers(BaseHandler):
    def __init__(self, subscription_service: SubscriptionService, user_service: UserService, support_service: SupportService):
        self.subscription_service = subscription_service
        self.user_service = user_service
        self.support_service = support_service
        super().__init__()

    def _register_handlers(self):
        # Команды
        self.router.message.register(self.start, CommandStart())

        # Основные колбэки
        self.router.callback_query.register(self.show_plan_options, F.data == "buy_subscription")
        self.router.callback_query.register(self.handle_choose_monthly, F.data == "choose_monthly")
        self.router.callback_query.register(self.handle_choose_traffic, F.data == "choose_traffic")
        self.router.callback_query.register(self.handle_my_subscription, F.data == "my_subscription")
        self.router.callback_query.register(self.handle_back_to_main, F.data.in_(["back_to_main", "back_to_main_from_tickets"]))

        # Поддержка
        self.router.callback_query.register(self.open_support_menu, F.data == "open_support")
        self.router.callback_query.register(self.create_support_ticket, F.data == "create_support_ticket")
        self.router.callback_query.register(self.view_my_tickets, F.data == "view_my_tickets")
        self.router.callback_query.register(self.handle_back_to_support_menu, F.data == "back_to_support")
        self.router.callback_query.register(self.open_ticket_detail, F.data.startswith("ticket_"))

        self.router.callback_query.register(self.handle_support, F.data == "support")
        self.router.callback_query.register(self.handle_user_tickets, F.data == "user_support_tickets")
        self.router.callback_query.register(self.handle_user_ticket_view, F.data.startswith("user_view_ticket:"))
        self.router.callback_query.register(self.handle_close_ticket, F.data.startswith("close_ticket:"))

        # FSM
        self.router.message.register(self.handle_months_input, PurchaseStates.choosing_months)
        self.router.message.register(self.handle_traffic_input, PurchaseStates.choosing_traffic)
        self.router.message.register(self.handle_support_message, SupportStates.waiting_for_message)

        # 💳 Оплата Stars
        self.router.pre_checkout_query.register(self.process_pre_checkout)

    # === /start ===
    async def start(self, message: Message):
        telegram_id = message.from_user.id
        await self.user_service.get_or_create_user(telegram_id)
        welcome_message = build_welcome_message(self.support_service.get_support_contact_info())
        await message.answer(welcome_message, reply_markup=get_user_main_keyboard(telegram_id))

    # === Поддержка ===
    async def open_support_menu(self, callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.edit_text(
            "🆘 Раздел поддержки.\n\nВы можете создать обращение или просмотреть свои предыдущие тикеты.",
            reply_markup=get_user_support_menu_keyboard()
        )

    async def create_support_ticket(self, callback: CallbackQuery, state: FSMContext):
        telegram_id = callback.from_user.id
        username = callback.from_user.username or f"user_{telegram_id}"

        tickets = await self.support_service.get_user_tickets(telegram_id)
        open_tickets = [t for t in tickets if t.status == "open"]
        if len(open_tickets) >= self.support_service.MAX_OPEN_TICKETS:
            await callback.message.answer(f"⚠️ У вас уже есть {len(open_tickets)} открытых тикета. Дождитесь ответа поддержки.",
                                          reply_markup=get_user_main_keyboard(telegram_id))
            return

        await state.set_state(SupportStates.waiting_for_message)
        await callback.message.edit_text("📝 Опишите вашу проблему одним сообщением.\nПосле этого тикет будет создан.\n\n✍️ Введите сообщение:")

    async def handle_support_message(self, message: Message, state: FSMContext):
        user_id = message.from_user.id
        username = message.from_user.username or f"user_{user_id}"
        text = message.text.strip()

        ticket = await self.support_service.create_support_ticket(user_id, username, text)
        if not ticket:
            await message.answer("⚠️ Превышен лимит открытых обращений.", reply_markup=get_user_main_keyboard(user_id))
            await state.clear()
            return

        msg_for_admin = await self.support_service.format_support_message_for_admin(user_id, username, text)
        logger.info(f"📨 Отправлено в поддержку: {msg_for_admin}")

        await message.answer(f"✅ Ваше обращение №{ticket.id} отправлено в поддержку.\nМы ответим как можно скорее 🙌",
                             reply_markup=get_user_main_keyboard(user_id))
        await state.clear()

    async def view_my_tickets(self, callback: CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        tickets = await self.support_service.get_user_tickets(user_id)
        msg = await self.support_service.format_ticket_list_for_user(tickets)
        markup = get_user_tickets_list_keyboard(tickets)
        await callback.message.edit_text(msg, reply_markup=markup)

    async def open_ticket_detail(self, callback: CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        ticket_id = int(callback.data.replace("ticket_", ""))
        ticket = await self.support_service.get_ticket_details(ticket_id, user_id)
        if not ticket:
            await callback.answer("Тикет не найден или уже закрыт.", show_alert=True)
            return
        msg = await self.support_service.format_ticket_details(ticket)
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="view_my_tickets")]])
        await callback.message.edit_text(msg, reply_markup=markup)

    async def handle_back_to_support_menu(self, callback: CallbackQuery, state: FSMContext):
        await self.open_support_menu(callback, state)

    # === Меню выбора типа подписки ===
    async def show_plan_options(self, callback: CallbackQuery, state: FSMContext):
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        await state.clear()
        telegram_id = callback.from_user.id

        result = await self.subscription_service.get_subscription_info(telegram_id)

        # Если есть активная подписка
        if result.success and result.subscription_info and result.subscription_info.is_active:
            info = result.subscription_info

            # 🔍 Определяем тип подписки корректно
            sub_type = "monthly" if info.expire_date else "traffic"
            if getattr(info, "data_limit_gb", 0) and info.data_limit_gb > 0:
                sub_type = "traffic"

            # Формируем сообщение
            msg = (
                f"🎉 У вас уже есть активная подписка:\n\n"
                f"📦 Тип: {'📅 Ежемесячная подписка' if sub_type == 'monthly' else '💾 По трафику'}\n"
                f"👤 Пользователь: {info.username}\n"
                f"📆 Действует до: {info.expire_date or '—'}\n"
                f"📎 Ссылка: {info.subscription_url or 'нет данных'}\n\n"
            )

            # В зависимости от типа — показываем нужную кнопку
            if sub_type == "monthly":
                msg += (
                    "⚠️ У вас активна месячная подписка.\n"
                    "Вы можете только продлить её срок.\n"
                    "Для перехода на тариф по трафику — обратитесь в поддержку."
                )
                keyboard = [
                    [InlineKeyboardButton(text="📅 Продлить подписку", callback_data="choose_monthly")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")],
                ]

            elif sub_type == "traffic":
                msg += (
                    "⚠️ У вас активен тариф по трафику.\n"
                    "Вы можете только докупить дополнительный объём.\n"
                    "Для перехода на месячную подписку — обратитесь в поддержку."
                )
                keyboard = [
                    [InlineKeyboardButton(text="💾 Докупить трафик", callback_data="choose_traffic")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")],
                ]

            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(msg, reply_markup=markup)
            return

        # Если подписки нет — стандартное меню
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"📅 По времени ({config.STAR_PRICE_PER_MONTH}⭐/мес)",
                    callback_data="choose_monthly",
                ),
                InlineKeyboardButton(
                    text=f"💾 По трафику ({config.STAR_PRICE_PER_GB}⭐/ГБ)",
                    callback_data="choose_traffic",
                ),
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")],
        ])
        await callback.message.edit_text("💎 Выберите тип подписки:", reply_markup=markup)


    # === Покупка ежемесячной ===
    async def handle_choose_monthly(self, callback: CallbackQuery, state: FSMContext):
        telegram_id = callback.from_user.id
        cur = await self.subscription_service.get_subscription_info(telegram_id)
        if cur.success and cur.subscription_info and cur.subscription_info.is_active:
            sub_type = detect_subscription_type(cur.subscription_info)
            if sub_type == "traffic":
                await callback.message.answer(
                    "❌ У вас активен трафиковый тариф — вы не можете оформить месячную подписку пока он активен. "
                    "Для смены тарифа обратитесь в поддержку."
                )
                await callback.message.answer("Возвращаю в меню.", reply_markup=get_user_main_keyboard(telegram_id))
                return

        await state.set_state(PurchaseStates.choosing_months)
        back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_main")]])
        await callback.message.edit_text(
            f"📅 На сколько месяцев хотите купить подписку?\n"
            f"💰 Цена: {config.STAR_PRICE_PER_MONTH}⭐ за 1 месяц\n"
            f"Введите число от 1 до 12:",
            reply_markup=back_kb,
        )

    # === Покупка по трафику ===
    async def handle_choose_traffic(self, callback: CallbackQuery, state: FSMContext):
        telegram_id = callback.from_user.id
        cur = await self.subscription_service.get_subscription_info(telegram_id)
        if cur.success and cur.subscription_info and cur.subscription_info.is_active:
            sub_type = detect_subscription_type(cur.subscription_info)
            if sub_type == "monthly":
                await callback.message.answer(
                    "❌ У вас активна помесячная подписка — докупить ГБ нельзя до её окончания. "
                    "Для смены тарифа обратитесь в поддержку."
                )
                await callback.message.answer("Возвращаю в меню.", reply_markup=get_user_main_keyboard(telegram_id))
                return

        await state.set_state(PurchaseStates.choosing_traffic)
        back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_main")]])
        await callback.message.edit_text(
            f"💾 Сколько ГБ вы хотите купить?\n"
            f"💰 Цена: {config.STAR_PRICE_PER_GB}⭐ за 1 ГБ\n"
            f"Введите число от 1 до 100:",
            reply_markup=back_kb,
        )

    # === FSM: месяцы ===
    async def handle_months_input(self, message: Message, state: FSMContext):
        if not message.text:
            return
        telegram_id = message.from_user.id

        cur = await self.subscription_service.get_subscription_info(telegram_id)
        if cur.success and cur.subscription_info and cur.subscription_info.is_active:
            sub_type = detect_subscription_type(cur.subscription_info)
            if sub_type == "traffic":
                await message.answer("❌ У вас активен трафиковый тариф — продление помесячной подписки недоступно.")
                await state.clear()
                await message.answer("Возвращаю в меню.", reply_markup=get_user_main_keyboard(telegram_id))
                return

        try:
            months = int(message.text.strip())
            if not 1 <= months <= 12:
                await message.answer("⚠️ Введите число от 1 до 12.")
                return

            price = months * config.STAR_PRICE_PER_MONTH
            payload = f"monthly:{months}:{telegram_id}"
            logger.info(f"➡️ Создание инвойса: {months} мес. за {price}⭐")

            await message.answer_invoice(
                title="Подписка VPN",
                description=f"📅 Подписка на {months} мес.\n💎 {price}⭐",
                payload=payload,
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="VPN Подписка", amount=price)],
            )
        except ValueError:
            await message.answer("❌ Введите корректное число от 1 до 12.")

    # === FSM: ГБ ===
    async def handle_traffic_input(self, message: Message, state: FSMContext):
        if not message.text:
            return
        telegram_id = message.from_user.id

        cur = await self.subscription_service.get_subscription_info(telegram_id)
        if cur.success and cur.subscription_info and cur.subscription_info.is_active:
            sub_type = detect_subscription_type(cur.subscription_info)
            if sub_type == "monthly":
                await message.answer("❌ У вас активна месячная подписка — докупить ГБ нельзя до её окончания.")
                await state.clear()
                await message.answer("Возвращаю в меню.", reply_markup=get_user_main_keyboard(telegram_id))
                return

        try:
            gb = int(message.text.strip())
            if not 1 <= gb <= 100:
                await message.answer("⚠️ Введите число от 1 до 100.")
                return

            price = gb * config.STAR_PRICE_PER_GB
            payload = f"traffic:{gb}:{telegram_id}"
            logger.info(f"➡️ Создание инвойса: {gb} ГБ за {price}⭐")

            await message.answer_invoice(
                title="VPN по трафику",
                description=f"💾 {gb} ГБ трафика\n💎 {price}⭐",
                payload=payload,
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="VPN Трафик", amount=price)],
            )
        except ValueError:
            await message.answer("❌ Введите корректное число от 1 до 100.")

    # === Обработка оплаты Stars ===
    async def process_pre_checkout(self, query: PreCheckoutQuery):
        payload = query.invoice_payload
        logger.info(f"💳 Pre-checkout Stars: {payload}")
        await query.answer(ok=True)

        try:
            plan, value, user_id = payload.split(":")
            user_id = int(user_id)
            value = int(value)

            if plan == "monthly":
                logger.info(f"🕒 Создание месячной подписки: {value} мес. для {user_id}")
                result = await self.subscription_service.purchase_monthly_subscription(user_id, value)
                plan_name = f"на {value} мес."
            else:
                logger.info(f"💾 Создание тарифного пакета: {value} ГБ для {user_id}")
                result = await self.subscription_service.purchase_gb_subscription(user_id, value)
                plan_name = f"{value} ГБ"

            if result.success:
                info = result.subscription_info
                from datetime import datetime

                sub_type = "traffic" if getattr(info, "data_limit_gb", 0) else "monthly"
                msg = "🎉 Ваша подписка активирована!\n\n"

                if sub_type == "monthly":
                    expire_dt = info.expire_date
                    expire_str = expire_dt.strftime("%d.%m.%Y %H:%M") if isinstance(expire_dt, datetime) else str(expire_dt)
                    days_left = 0
                    if isinstance(expire_dt, datetime):
                        days_left = max(0, (expire_dt - datetime.utcnow()).days)

                    msg += (
                        f"📅 Тип: Месячная\n"
                        f"⏳ Осталось: {days_left} дн.\n"
                        f"📆 До: {expire_str}\n\n"
                        f"👤 Пользователь: {info.username}\n"
                        f"📎 Ссылка: {info.subscription_url or 'нет данных'}\n\n"
                        f"💎 Спасибо, что пользуетесь нашим сервисом!"
                    )

                else:
                    used = getattr(info, "used_traffic_gb", 0) or 0
                    total = getattr(info, "data_limit_gb", 0) or 0
                    percent = round((used / total) * 100, 1) if total > 0 else 0

                    msg += (
                        f"💾 Тип: По трафику\n"
                        f"📊 Использовано: {used:.2f} ГБ / {total:.2f} ГБ ({percent}%)\n\n"
                        f"👤 Пользователь: {info.username}\n"
                        f"📎 Ссылка: {info.subscription_url or 'нет данных'}\n\n"
                        f"💎 Спасибо, что пользуетесь нашим сервисом!"
                    )

                await query.bot.send_message(user_id, msg, reply_markup=get_user_main_keyboard(user_id))

            else:
                await query.bot.send_message(
                    user_id,
                    f"⚠️ Оплата прошла, но подписку не удалось активировать.\nОшибка: {result.error_message}",
                )

        except Exception as e:
            logger.exception(f"Ошибка при создании подписки после оплаты: {e}")
            await query.bot.send_message(
                query.from_user.id, "❌ Произошла ошибка при активации подписки. Мы уже разбираемся."
            )


    # === Моя подписка ===
    async def handle_my_subscription(self, callback: CallbackQuery, state: FSMContext):
        telegram_id = callback.from_user.id
        await state.clear()
        result = await self.subscription_service.get_subscription_info(telegram_id)
        await self._handle_subscription_result(callback, result, telegram_id)

    # === Назад в меню ===
    async def handle_back_to_main(self, callback: CallbackQuery, state: FSMContext):
        await state.clear()
        user_id = callback.from_user.id
        welcome_message = build_welcome_message(self.support_service.get_support_contact_info())
        await callback.message.edit_text(welcome_message, reply_markup=get_user_main_keyboard(user_id))

    # === Вывод подписки ===
    async def _handle_subscription_result(self, callback: CallbackQuery, result: SubscriptionResult, user_id: int):
        """Показывает пользователю детальную информацию о его подписке."""
        if not result.success or not result.subscription_info:
            await callback.message.edit_text(
                f"❌ {result.error_message or 'Подписка не найдена.'}",
                reply_markup=get_user_main_keyboard(user_id)
            )
            return

        info = result.subscription_info
        data_limit = getattr(info, "data_limit_gb", 0) or 0
        sub_type = "traffic" if data_limit > 0 else "monthly"

        # безопасное определение даты
        expire = info.expire_date
        if isinstance(expire, str):
            expire_str = expire
            days_left = 0
        else:
            expire_str = expire.strftime("%d.%m.%Y %H:%M") if expire else "—"
            now = datetime.datetime.utcnow()
            days_left = max(0, (expire - now).days) if expire else 0

        # --- Формирование текста ---
        if sub_type == "monthly":
            msg = (
                f"🎉 Ваша подписка активна!\n\n"
                f"📅 Тип: Месячная\n"
                f"⏳ Осталось: {days_left} дн.\n"
                f"📆 До: {expire_str}\n\n"
                f"👤 Пользователь: `{info.username}`\n"
                f"📎 Ссылка: {info.subscription_url or 'нет данных'}\n\n"
                f"💎 Спасибо, что пользуетесь нашим сервисом!"
            )
            buttons = [
                [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="choose_monthly")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
            ]

        else:
            used = getattr(info, "used_traffic_gb", 0)
            total = getattr(info, "data_limit_gb", 0)
            percent = 0
            if total > 0:
                percent = round((used / total) * 100, 1)
                if percent > 100:
                    percent = 100

            msg = (
                f"🎉 Ваша подписка по трафику!\n\n"
                f"💾 Объем: {total:.1f} ГБ\n"
                f"📊 Использовано: {used:.1f} ГБ ({percent}%)\n"
                f"📆 Статус: {'🟢 Активна' if info.is_active else '🔴 Неактивна'}\n\n"
                f"👤 Пользователь: `{info.username}`\n"
                f"📎 Ссылка: {info.subscription_url or 'нет данных'}\n\n"
                f"💎 Спасибо, что пользуетесь нашим сервисом!"
            )
            buttons = [
                [InlineKeyboardButton(text="💾 Докупить трафик", callback_data="choose_traffic")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
            ]

        # --- Добавляем конфиги (если есть) ---
        if getattr(info, "configs", None):
            msg += "\n\n🔌 Конфигурации для подключения:\n"
            for i, conf in enumerate(info.configs[:3], start=1):
                msg += f"{i}. `{conf}`\n"

        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(msg, reply_markup=markup, parse_mode="Markdown")

    # === Меню поддержки ===
    async def handle_support(self, callback: CallbackQuery, state: FSMContext):
        """Главное меню поддержки"""
        from presentation.keyboards.support_keyboards import get_support_keyboard
        await state.clear()
        await callback.message.edit_text(
            "🆘 Техническая поддержка\n\n"
            "Здесь вы можете задать вопрос или сообщить о проблеме.",
            reply_markup=get_support_keyboard()
        )

    @staticmethod
    def _build_ticket_text(ticket) -> str:
        created_at = getattr(ticket, "created_at", None)
        created = created_at.strftime('%d.%m.%Y %H:%M') if created_at else "—"
        status_open = ticket.status == "open"
        status_icon = "🟢" if status_open else "🔒"

        text = (
            f"{status_icon} <b>Тикет #{ticket.id}</b>\n"
            f"🕒 {created}\n"
            f"💬 {ticket.message}\n"
        )

        if getattr(ticket, "response", None):
            text += f"📣 Ответ: {ticket.response}\n"

        text += f"📌 Статус: {'Открыт' if status_open else 'Закрыт'}"
        return text

    @staticmethod
    def _build_ticket_markup(ticket) -> Optional[InlineKeyboardMarkup]:
        if ticket.status != "open":
            return None

        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Закрыть тикет", callback_data=f"close_ticket:{ticket.id}")]]
        )

    # === Мои обращения ===
    async def handle_user_tickets(self, callback: CallbackQuery, state: FSMContext):
        from presentation.keyboards.support_keyboards import get_support_keyboard

        await state.clear()
        telegram_id = callback.from_user.id
        tickets = await self.support_service.get_user_tickets(telegram_id)

        if not tickets:
            await callback.message.edit_text(
                "📭 У вас пока нет обращений.",
                reply_markup=get_support_keyboard()
            )
            return

        # Формируем список сообщений (каждый тикет — отдельный блок)
        for ticket in tickets:
            text = self._build_ticket_text(ticket)
            markup = self._build_ticket_markup(ticket)

            await callback.message.answer(text, reply_markup=markup, parse_mode="HTML")

        # Отдельным сообщением показываем меню поддержки
        await callback.message.answer(
            "Главное меню поддержки:",
            reply_markup=get_support_keyboard()
        )

        # Удаляем старое сообщение с кнопкой «Мои обращения»
        try:
            await callback.message.delete()
        except Exception:
            pass


    # === Просмотр конкретного тикета ===
    async def handle_user_ticket_view(self, callback: CallbackQuery, state: FSMContext):
        from presentation.keyboards.support_keyboards import get_support_keyboard
        ticket_id = int(callback.data.split(":")[1])
        telegram_id = callback.from_user.id
        tickets = await self.support_service.get_user_tickets(telegram_id)
        ticket = next((t for t in tickets if t.id == ticket_id), None)

        if not ticket:
            await callback.message.edit_text("⚠️ Обращение не найдено.", reply_markup=get_support_keyboard())
            return

        msg = (
            f"📄 Обращение #{ticket.id}\n\n"
            f"💬 Сообщение:\n{ticket.message}\n\n"
            f"📅 Создано: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"📌 Статус: {'🟢 Открыт' if ticket.status == 'open' else '🔴 Закрыт'}"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="user_support_tickets")]
        ])
        await callback.message.edit_text(msg, reply_markup=kb)

    # === Пользователь закрывает тикет ===
    async def handle_close_ticket(self, callback: CallbackQuery):
        try:
            _, ticket_id_str = callback.data.split(":")
            ticket_id = int(ticket_id_str)
            success = await self.support_service.close_ticket(ticket_id)

            if success:
                ticket = await self.support_service.get_ticket_details(ticket_id, callback.from_user.id)
                if ticket:
                    text = self._build_ticket_text(ticket)
                else:
                    text = (
                        f"🔒 <b>Тикет #{ticket_id}</b>\n"
                        "📌 Статус: Закрыт"
                    )
                await callback.message.edit_text(text, parse_mode="HTML")
                await callback.answer("✅ Тикет закрыт")
            else:
                await callback.answer(
                    f"⚠️ Не удалось закрыть тикет #{ticket_id}. Возможно, он уже закрыт.",
                    show_alert=True
                )
        except Exception as e:
            logger.exception(f"Ошибка при закрытии тикета пользователем: {e}")
            await callback.answer("❌ Произошла ошибка при закрытии тикета.", show_alert=True)
