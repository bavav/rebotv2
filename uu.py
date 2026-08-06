import sqlite3
import os

db_path = 'database.db'
os.remove(db_path)
# Подключение
connection = sqlite3.connect(db_path)
cursor = connection.cursor()

# Пример запроса: выбрать всех пользователей
cursor.execute('SELECT * FROM users')

# Получение и вывод результатов
users = cursor.fetchall()
for user in users:
    print(user)


# Закрытие соединения
connection.close()
