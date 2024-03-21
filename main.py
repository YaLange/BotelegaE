import random
import configparser
import sqlalchemy as sq
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from sqlalchemy.orm import sessionmaker
from models import User, Word, CommonWord


def db_get_user_list(engine):
    session = (sessionmaker(bind=engine))()
    users = session.query(User).all()
    users = [user.cid for user in users]
    session.close()
    return users


def db_add_user(engine, user_id):
    session = (sessionmaker(bind=engine))()
    session.add(User(cid=user_id))
    session.commit()
    session.close()


def db_get_words(engine, user_id):
    session = (sessionmaker(bind=engine))()
    words = session.query(Word.word, Word.translate) \
        .join(User, User.id == Word.id_user) \
        .filter(User.cid == user_id).all()
    common_words = session.query(CommonWord.word, CommonWord.translate).all()
    result = common_words + words
    session.close()
    return result


def db_add_word(engine, cid, word, translate):
    session = (sessionmaker(bind=engine))()
    id_user = session.query(User.id).filter(User.cid == cid).first()[0]
    session.add(Word(word=word, translate=translate, id_user=id_user))
    session.commit()
    session.close()


def db_delete_word(engine, cid, word):
    session = (sessionmaker(bind=engine))()
    id_user = session.query(User.id).filter(User.cid == cid).first()[0]
    session.query(Word).filter(Word.id_user == id_user, Word.word == word).delete()
    session.commit()
    session.close()


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0


print('Start telegram bot...')

config = configparser.ConfigParser()
config.read('settings.ini')

engine = sq.create_engine(config['posgres']['DSN'])

state_storage = StateMemoryStorage()
token_bot = config['bot']['token']
bot = TeleBot(token_bot, state_storage=state_storage)

known_users = db_get_user_list(engine)
print(f'Loaded {len(known_users)} users')
userStep = {}
buttons = []

welcome_text = '''Привет 👋 Давай попрактикуемся в английском языке!

Воспользуйся инструментами:

Добавить слово ➕,
удалить слово 🔙.
Ну что, начнём ⬇️?'''


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    userStep[cid] = 0
    if cid not in known_users:
        known_users.append(cid)
        db_add_user(engine, cid)
        userStep[cid] = 0
        bot.send_message(cid, welcome_text)
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []
    words4 = random.sample(db_get_words(engine, cid), 4)
    word = words4[0]
    print(f'Choosing word: {word}')
    target_word = word[0]  # брать из БД
    translate = word[1]  # брать из БД
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    others = [word for word, _ in words4[1:]]
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        print("Deleting ", message.chat.id, data['target_word'])  # удалить из БД
        db_delete_word(engine, message.chat.id, data['target_word'])
        bot.send_message(message.chat.id, "Слово удалено")


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    userStep[cid] = 1
    bot.send_message(cid, "Введите слово на английском")
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    cid = message.chat.id

    if userStep[cid] == 0:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            target_word = data['target_word']
            if text == target_word:
                hint = show_target(data)
                hint_text = ["Отлично!❤", hint]
                # next_btn = types.KeyboardButton(Command.NEXT)
                # add_word_btn = types.KeyboardButton(Command.ADD_WORD)
                # delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
                # buttons.extend([next_btn, add_word_btn, delete_word_btn])
                hint = show_hint(*hint_text)
            else:
                for btn in buttons:
                    if btn.text == text:
                        btn.text = text + '❌'
                        break
                hint = show_hint("Ошибка!", f"Попробуй ещё раз {data['translate_word']}")
        markup.add(*buttons)
        bot.send_message(message.chat.id, hint, reply_markup=markup)
        create_cards(message)
    elif userStep[cid] == 1:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['target_word'] = text
            bot.send_message(cid, "Введите перевод слова на русском")
            bot.set_state(message.from_user.id, MyStates.translate_word, message.chat.id)
            userStep[cid] = 2
    elif userStep[cid] == 2:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['translate_word'] = text
            db_add_word(engine, cid, data['target_word'], data['translate_word'])
            bot.send_message(cid, "Слово добавлено")
            userStep[cid] = 0
            create_cards(message)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)
