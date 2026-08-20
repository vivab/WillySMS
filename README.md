# tabachka-bot

Telegram-бот для собственного/разрешённого SMS-сервиса.

## Запуск

1. Установить зависимости:
   `pip install -r requirements.txt`
2. Задать переменные окружения из `.env.example`.
3. Запустить:
   `python bot.py`

## Основные команды супер-админа

- `/add Самокат 0.5$`
- `/list`
- `/del ID`
- `/addadmin TELEGRAM_ID`
- `/deladmin TELEGRAM_ID`
- `/addnumber +XXXXXXXXXXX`

## Админ

- `/take ID` — атомарно взять заявку.

Коды проверяются администратором вручную. Модуль SMS является адаптером для собственного/разрешённого SMS-провайдера и не перехватывает сторонние OTP.
