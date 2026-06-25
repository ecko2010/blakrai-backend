import os

directory = r'c:\Users\ahmed\OneDrive\Desktop\blakrai-main\app\admin\templates'

translations = {
    # Users page
    "Username, ім'я, Telegram ID...": "Username, name, Telegram ID...",
    "Пошук": "Search",
    "Всі": "All",
    "Фільтр": "Filter",
    "Скинути": "Reset",
    "загалом": "total",
    "Стор.": "Page",
    "ІМ'Я": "NAME",
    "МОВА": "LANGUAGE",
    "БАН": "BAN",
    "ЗАРЕЄСТРОВАНО": "REGISTERED",
    "ДІЇ": "ACTIONS",
    "Змінити тір": "Change tier",
    "заблоковано": "blocked",
    "Заблокувати": "Block",
    "Розблокувати": "Unblock",

    # System page
    "Таблиці БД": "Database Tables",
    "таблиць": "tables",
    "ТАБЛИЦЯ": "TABLE",
    "РЯДКІВ": "ROWS",
    "задач": "tasks",
    "Останній скан": "Last scan",
    "Конфігурація": "Configuration",
    "Пам'ять": "Memory",
    "Клієнтів": "Clients",
    "Ключів": "Keys",
    "ключів": "keys",
    "Задачі планувальника": "Scheduler tasks",
    "ТРИГЕР": "TRIGGER",
    "НАСТУПНИЙ ЗАПУСК": "NEXT RUN",
    
    # Generic missing
    "Ок": "Ok",
    "Деталі": "Details",
    "Зберегти": "Save",
    "Видалити": "Delete",
    "Редагувати": "Edit",
    "Ні": "No",
    "Так": "Yes",
    "Назад": "Back",
    "Ціна": "Price",
    "Статус": "Status",
    "Тип": "Type",
    "Значення": "Value",
    "Дата": "Date",
    "Час": "Time",
    "Аналіз": "Analysis",
}

for filename in os.listdir(directory):
    if filename.endswith('.html'):
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for uk, en in translations.items():
            content = content.replace(uk, en)
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

print("Applied second batch of translations!")
