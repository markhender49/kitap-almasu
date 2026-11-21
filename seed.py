from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent
DB = ROOT / "kitap_almasu.db"


def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS books (
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL,
          genre TEXT NOT NULL, language TEXT NOT NULL, condition TEXT NOT NULL,
          city TEXT NOT NULL, owner TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
          cover TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'available'
        );
        CREATE TABLE IF NOT EXISTS requests (
          id INTEGER PRIMARY KEY AUTOINCREMENT, book_id INTEGER NOT NULL REFERENCES books(id),
          requester TEXT NOT NULL, offer TEXT NOT NULL, message TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'pending'
        );
        CREATE TABLE IF NOT EXISTS users (
          name TEXT PRIMARY KEY, city TEXT NOT NULL DEFAULT '', rating REAL NOT NULL DEFAULT 5,
          reviews INTEGER NOT NULL DEFAULT 0, swaps INTEGER NOT NULL DEFAULT 0, joined TEXT NOT NULL DEFAULT '2026'
        );
        """)
        book_count = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        if book_count == 0:
            seed = [
              ("Көксерек", "Мұхтар Әуезов", "Классика", "Қазақша", "Өте жақсы", "Алматы", "Айдана", "Қазақ әдебиетінің ықшам әрі әсерлі повесі.", "#e8e3d4"),
              ("Абай жолы", "Мұхтар Әуезов", "Роман", "Қазақша", "Жақсы", "Астана", "Нұрлан", "Екі кітаптық басылым. Мұқабасында аздаған із бар.", "#d6e1d6"),
              ("Маленький принц", "Антуан де Сент-Экзюпери", "Повесть", "Русский", "Өте жақсы", "Алматы", "Мира", "Жылы иллюстрациялары бар шағын басылым.", "#f0dfc7"),
              ("1984", "Джордж Оруэлл", "Антиутопия", "Русский", "Жақсы", "Шымкент", "Данияр", "Бумажное издание, страницы целые.", "#d9dce5"),
              ("The Hobbit", "J. R. R. Tolkien", "Фэнтези", "English", "Жақсы", "Астана", "Алина", "Paperback edition. Looking for another fantasy novel.", "#e5dcc8"),
              ("Қан мен тер", "Әбдіжәміл Нұрпейісов", "Роман", "Қазақша", "Қанағаттанарлық", "Қарағанды", "Ермек", "Оқуға жарамды, мұқабасы тозған.", "#dedbd0"),
            ]
            db.executemany("INSERT INTO books(title,author,genre,language,condition,city,owner,description,cover) VALUES(?,?,?,?,?,?,?,?,?)", seed)
        users = [
          ("Айдана", "Алматы", 4.9, 38, 31, "2025"), ("Нұрлан", "Астана", 4.8, 26, 22, "2025"),
          ("Мира", "Алматы", 5.0, 17, 15, "2026"), ("Данияр", "Шымкент", 4.6, 13, 10, "2025"),
          ("Алина", "Астана", 4.9, 21, 18, "2025"), ("Ермек", "Қарағанды", 4.5, 8, 6, "2026"),
          ("София", "Ақтөбе", 4.9, 19, 16, "2025"), ("Арман", "Павлодар", 4.7, 12, 9, "2025"),
          ("Жанель", "Өскемен", 5.0, 11, 10, "2026"), ("Тимур", "Атырау", 4.4, 7, 5, "2026"),
          ("Әлия", "Тараз", 4.8, 16, 14, "2025"), ("Мадина", "Қостанай", 4.9, 14, 12, "2025"),
          ("Руслан", "Қызылорда", 4.2, 5, 3, "2026"), ("Дина", "Алматы", 4.7, 9, 8, "2026"),
        ]
        db.executemany("INSERT OR IGNORE INTO users(name,city,rating,reviews,swaps,joined) VALUES(?,?,?,?,?,?)", users)

        # Seed ~50 additional books once, preserving user data and prior demo additions.
        if db.execute("SELECT 1 FROM books WHERE title='О дивный новый мир' LIMIT 1").fetchone() is None:
            extra = [
              ("Преступление и наказание", "Фёдор Достоевский", "Классика", "Русский"),
              ("Мастер и Маргарита", "Михаил Булгаков", "Классика", "Русский"),
              ("Война и мир", "Лев Толстой", "Роман", "Русский"),
              ("Анна Каренина", "Лев Толстой", "Роман", "Русский"),
              ("Идиот", "Фёдор Достоевский", "Классика", "Русский"),
              ("Отцы и дети", "Иван Тургенев", "Классика", "Русский"),
              ("Герой нашего времени", "Михаил Лермонтов", "Классика", "Русский"),
              ("Мёртвые души", "Николай Гоголь", "Классика", "Русский"),
              ("Белые ночи", "Фёдор Достоевский", "Повесть", "Русский"),
              ("Доктор Живаго", "Борис Пастернак", "Роман", "Русский"),
              ("О дивный новый мир", "Олдос Хаксли", "Антиутопия", "Русский"),
              ("451° по Фаренгейту", "Рэй Брэдбери", "Антиутопия", "Русский"),
              ("Марсианские хроники", "Рэй Брэдбери", "Фантастика", "Русский"),
              ("Цветы для Элджернона", "Дэниел Киз", "Фантастика", "Русский"),
              ("Дюна", "Фрэнк Герберт", "Фантастика", "Русский"),
              ("Солярис", "Станислав Лем", "Фантастика", "Русский"),
              ("Пикник на обочине", "Аркадий и Борис Стругацкие", "Фантастика", "Русский"),
              ("Трудно быть богом", "Аркадий и Борис Стругацкие", "Фантастика", "Русский"),
              ("Игра престолов", "Джордж Р. Р. Мартин", "Фэнтези", "Русский"),
              ("Ведьмак: Последнее желание", "Анджей Сапковский", "Фэнтези", "Русский"),
              ("Гарри Поттер и философский камень", "Джоан Роулинг", "Фэнтези", "Русский"),
              ("Хоббит", "Дж. Р. Р. Толкин", "Фэнтези", "Русский"),
              ("Маленькие женщины", "Луиза Мэй Олкотт", "Роман", "Русский"),
              ("Джейн Эйр", "Шарлотта Бронте", "Роман", "Русский"),
              ("Гордость и предубеждение", "Джейн Остин", "Роман", "Русский"),
              ("Убить пересмешника", "Харпер Ли", "Роман", "Русский"),
              ("Великий Гэтсби", "Фрэнсис Скотт Фицджеральд", "Роман", "Русский"),
              ("Повелитель мух", "Уильям Голдинг", "Роман", "Русский"),
              ("Алхимик", "Пауло Коэльо", "Роман", "Русский"),
              ("Шантарам", "Грегори Дэвид Робертс", "Роман", "Русский"),
              ("Сапарнама", "Ыбырай Алтынсарин", "Қазақ әдебиеті", "Қазақша"),
              ("Қара сөздер", "Абай Құнанбайұлы", "Қазақ әдебиеті", "Қазақша"),
              ("Менің атым Қожа", "Бердібек Соқпақбаев", "Повесть", "Қазақша"),
              ("Балалық шаққа саяхат", "Бердібек Соқпақбаев", "Повесть", "Қазақша"),
              ("Ұшқан ұя", "Бауыржан Момышұлы", "Естелік", "Қазақша"),
              ("Қилы заман", "Мұхтар Әуезов", "Тарихи роман", "Қазақша"),
              ("Ақбілек", "Жүсіпбек Аймауытов", "Роман", "Қазақша"),
              ("Шұғаның белгісі", "Бейімбет Майлин", "Повесть", "Қазақша"),
              ("Көшпенділер", "Ілияс Есенберлин", "Тарихи роман", "Қазақша"),
              ("Алтын орда", "Ілияс Есенберлин", "Тарихи роман", "Қазақша"),
              ("Қарғын", "Дулат Исабеков", "Роман", "Қазақша"),
              ("Ақиқат пен аңыз", "Әзілхан Нұршайықов", "Естелік", "Қазақша"),
              ("Мен", "Сәкен Сейфуллин", "Естелік", "Қазақша"),
              ("Ұлпан", "Ғабит Мүсірепов", "Роман", "Қазақша"),
              ("Ботагөз", "Сәбит Мұқанов", "Роман", "Қазақша"),
              ("Көксерек", "Мұхтар Әуезов", "Повесть", "Қазақша"),
              ("The Great Gatsby", "F. Scott Fitzgerald", "Classic", "English"),
              ("To Kill a Mockingbird", "Harper Lee", "Novel", "English"),
              ("Pride and Prejudice", "Jane Austen", "Romance", "English"),
              ("The Catcher in the Rye", "J. D. Salinger", "Novel", "English"),
              ("Animal Farm", "George Orwell", "Dystopia", "English"),
            ]
            cities = ["Алматы", "Астана", "Шымкент", "Қарағанды", "Ақтөбе", "Павлодар", "Өскемен", "Атырау", "Тараз", "Қостанай", "Қызылорда", "Ақтау", "Орал", "Петропавл", "Түркістан"]
            owners = [u[0] for u in users]
            conditions = ["Өте жақсы", "Жақсы", "Жақсы", "Қанағаттанарлық"]
            covers = ["#e8e3d4", "#d6e1d6", "#f0dfc7", "#d9dce5", "#e5dcc8", "#dedbd0", "#e3d6d1", "#d9e0d9"]
            rows = []
            for i, (title, author, genre, language) in enumerate(extra):
                owner = owners[(i * 7 + 3) % len(owners)]
                city = next(u[1] for u in users if u[0] == owner)
                rows.append((title, author, genre, language, conditions[i % len(conditions)], city, owner,
                             f"Книга читана аккуратно. Владелец открыт к обмену и встрече в городе {city}.", covers[i % len(covers)]))
            db.executemany("INSERT INTO books(title,author,genre,language,condition,city,owner,description,cover) VALUES(?,?,?,?,?,?,?,?,?)", rows)

        # Seed several realistic incoming offers for the exchange dashboard.
        if db.execute("SELECT 1 FROM requests WHERE requester='София' LIMIT 1").fetchone() is None:
            demo_requests = [(1, "София", "Книжный вор", "Могу передать при встрече в центре"),
                             (2, "Арман", "Марсианские хроники", "Состояние отличное, буду в Астане в субботу"),
                             (4, "Жанель", "The Name of the Wind", "Предложу фэнтези на английском")]
            valid = [r for r in demo_requests if db.execute("SELECT status FROM books WHERE id=?", (r[0],)).fetchone() and db.execute("SELECT status FROM books WHERE id=?", (r[0],)).fetchone()[0] == "available"]
            db.executemany("INSERT INTO requests(book_id,requester,offer,message) VALUES(?,?,?,?)", valid)
            db.executemany("UPDATE books SET status='pending' WHERE id=?", [(r[0],) for r in valid])



