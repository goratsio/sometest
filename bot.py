import logging
from telegram import Update, Message, ChatPermissions
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация бота
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
ADMIN_GROUP_ID = -123456789  # ID группы для уведомлений (замените на реальный)

def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start"""
    update.message.reply_text('Привет! Я бот-модератор. Используй @admin или /report для жалоб.')

def handle_report(update: Update, context: CallbackContext) -> None:
    """Обработчик команд @admin, /report и подобных"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    
    if chat.type == 'private':
        update.message.reply_text('Эта команда работает только в группах.')
        return
    
    # Формируем ссылки на пользователя и сообщение
    user_link = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    message_link = f'<a href="https://t.me/c/{str(chat.id)[4:]}/{message.message_id}">сообщение</a>'
    
    # Отправляем уведомление в группу админов
    context.bot.send_message(
        ADMIN_GROUP_ID,
        f'🚨 Жалоба от {user_link} в чате "{chat.title}"\n'
        f'Ссылка на {message_link}',
        parse_mode='HTML'
    )
    
    # Подтверждаем пользователю
    message.reply_text(
        'Ваша жалоба отправлена администраторам. Спасибо!',
        reply_to_message_id=message.message_id
    )

def delete_service_messages(update: Update, context: CallbackContext) -> None:
    """Удаление системных сообщений"""
    message = update.effective_message
    if message and (message.left_chat_member or message.new_chat_members or message.pinned_message):
        try:
            message.delete()
        except Exception as e:
            logger.warning(f'Не удалось удалить системное сообщение: {e}')

def ban_user(update: Update, context: CallbackContext) -> None:
    """Бан пользователя (команда для админов)"""
    if update.effective_chat.type == 'private':
        update.message.reply_text('Эта команда работает только в группах.')
        return
    
    # Проверяем права пользователя
    user = update.effective_user
    member = context.bot.get_chat_member(update.effective_chat.id, user.id)
    if member.status not in ('administrator', 'creator'):
        update.message.reply_text('У вас нет прав для использования этой команды.')
        return
    
    # Получаем пользователя для бана (из реплая или из аргументов)
    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            target_user_id = int(context.args[0])
            target_user = context.bot.get_chat_member(update.effective_chat.id, target_user_id).user
        except (ValueError, IndexError):
            pass
    
    if not target_user:
        update.message.reply_text('Используйте команду в ответ на сообщение пользователя или укажите его ID.')
        return
    
    # Баним пользователя
    try:
        context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_user.id,
            revoke_messages=True
        )
        update.message.reply_text(f'Пользователь {target_user.full_name} забанен.')
    except Exception as e:
        update.message.reply_text(f'Ошибка: {e}')

def unban_user(update: Update, context: CallbackContext) -> None:
    """Разбан пользователя (команда для админов)"""
    if update.effective_chat.type == 'private':
        update.message.reply_text('Эта команда работает только в группах.')
        return
    
    # Проверяем права пользователя
    user = update.effective_user
    member = context.bot.get_chat_member(update.effective_chat.id, user.id)
    if member.status not in ('administrator', 'creator'):
        update.message.reply_text('У вас нет прав для использования этой команды.')
        return
    
    # Получаем пользователя для разбана
    if not context.args:
        update.message.reply_text('Укажите ID пользователя для разбана.')
        return
    
    try:
        target_user_id = int(context.args[0])
        context.bot.unban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target_user_id,
            only_if_banned=True
        )
        update.message.reply_text(f'Пользователь с ID {target_user_id} разбанен.')
    except (ValueError, IndexError):
        update.message.reply_text('Укажите корректный ID пользователя.')
    except Exception as e:
        update.message.reply_text(f'Ошибка: {e}')

def error_handler(update: Update, context: CallbackContext) -> None:
    """Обработчик ошибок"""
    logger.error(msg='Ошибка при обработке сообщения:', exc_info=context.error)
    if update.effective_message:
        update.effective_message.reply_text('Произошла ошибка. Пожалуйста, попробуйте позже.')

def main() -> None:
    """Запуск бота"""
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # Обработчики команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("report", handle_report))
    dispatcher.add_handler(CommandHandler("ban", ban_user))
    dispatcher.add_handler(CommandHandler("unban", unban_user))
    
    # Обработчики сообщений
    dispatcher.add_handler(MessageHandler(
        Filters.status_update & ~Filters.command, 
        delete_service_messages
    ))
    dispatcher.add_handler(MessageHandler(
        Filters.regex(r'(?i)@admin(s)?') & ~Filters.command, 
        handle_report
    ))
    
    # Обработчик ошибок
    dispatcher.add_error_handler(error_handler)

    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
