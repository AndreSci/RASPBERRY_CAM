import sqlite3
import datetime


class SQLClass:

    def __init__(self, db_file='./database/wheels_cam.db'):
        self.conn = sqlite3.connect(db_file)
        self.create_table_guests()

    def create_table_guests(self):
        query = """
        CREATE TABLE IF NOT EXISTS guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            first_name TEXT,
            last_name TEXT,
            car_number TEXT,
            datetime_create TIMESTAMP,
            datetime_enter TIMESTAMP,
            datetime_leave TIMESTAMP
        );
        """
        self.conn.execute(query)
        self.conn.commit()

    def add_guest(self, user_id, first_name, last_name, car_number):
        now = datetime.datetime.now()
        now = str(now.strftime("%Y-%m-%d/%H.%M.%S"))
        query = f"""
        INSERT INTO guests
        (user_id, first_name, last_name, car_number, datetime_create, datetime_enter, datetime_leave)
        VALUES
        ({user_id}, '{first_name}', '{last_name}', '{car_number}', '{now}', NULL, NULL)
        """
        self.conn.execute(query)
        self.conn.commit()
        print(f"Guest {first_name} {last_name} added.")

    def get_guests(self):
        query = "SELECT * FROM guests"
        cursor = self.conn.execute(query)
        guests = cursor.fetchall()
        return guests


if __name__ == '__main__':

    db = SQLClass()

    db.add_guest(2020, 'Тест_Имя', 'Тест_Фамилия', 'А100АА999')

    print(db.get_guests())