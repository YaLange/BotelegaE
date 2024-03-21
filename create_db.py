import sqlalchemy as sq
from sqlalchemy.orm import sessionmaker
from models import create_tables, User, Word, CommonWord
import configparser


def create_db(engine):

    common_words = (
        ('World', 'Мир'),
        ('Traveler', 'Путешественник'),
        ('Country', 'Страна'),
        ('City', 'Город'),
        ('Sea', 'Море'),
        ('Ocean', 'Океан'),
        ('River', 'Река'),
        ('Forest', 'Лес'),
        ('Beach', 'Пляж'),
        ('Car', 'Машина'),
        ('Ship', 'Корабль'),
        ('Airplane', 'Самолет'),
        ('Train', 'Поезд'),
        ('Dog', 'Собака'),
        ('Cat', 'Кошка'),
        ('Book', 'Книга'),
        ('Magazine', 'Журнал'),
        ('House', 'Дом'),
        ('Family', 'Семья')
    )

    create_tables(engine)

    session = (sessionmaker(bind=engine))()

    for row in common_words:
        session.add(CommonWord(word=row[0], translate=row[1]))
    session.commit()
    session.close()


config = configparser.ConfigParser()
config.read('settings.ini')

engine = sq.create_engine(config['posgres']['DSN'])

create_db(engine)
