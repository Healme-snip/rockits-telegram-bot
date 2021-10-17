# Телеграм бот для добавления записей в google sheets

## Требования

- `python >= 3.7`
- json ключ для google service account

## Подготовка

1. Установите зависимости
    ```bash
    pip install -r requirements.txt
    ```
2. Скопируйте `settings.json`
    ```bash
    cp default.settings.json settings.json
    ```
3. Подставьте токен, путь к json ключу и email в `settings.json`

    ```jsonc
    // settings.json

    {
        "tg": {
            "token": "0000000000:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" // токен телеграм бота
        },
        "gsheet": {
            "secret_file": "secret.json",            // путь к ключу google service account
            "spreadsheet_title": "Тестовое задание", // название таблицы
            "worksheet_title": "bot-rows",           // название лиcта
            "writer_emails": [                       // список email-ов, которым нужно дать доступ на запись
                "example@gmail.com"
            ]
        }
    }
    ```

4. Запуск
    ```bash
    python3 bot.py
    ```