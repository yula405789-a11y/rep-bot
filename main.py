import telebot
import sqlite3
import random
import time
import threading

from datetime import datetime
from telebot import types

# =====================================================
# SETTINGS
# =====================================================

TOKEN = "8863031163:AAF8kfQ1LtyStYVCTspEkirkUh7z-IfmLXA"
ADMIN_ID = 8413061759

bot = telebot.TeleBot(
    TOKEN,
    parse_mode="HTML"
)

# =====================================================
# DATABASE
# =====================================================

conn = sqlite3.connect(
    "rep.db",
    check_same_thread=False
)

cursor = conn.cursor()

# =====================================================
# TABLES
# =====================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    fake_id TEXT,
    username TEXT,
    reg_date INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS reps(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user INTEGER,
    to_user INTEGER,
    rep_type TEXT,
    reason TEXT,
    photo TEXT,
    date INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS bans(
    user_id INTEGER PRIMARY KEY,
    reason TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS mutes(
    user_id INTEGER PRIMARY KEY,
    mute_until INTEGER,
    reason TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS reports(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user INTEGER,
    target_user INTEGER,
    reason TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS antispam(
    user_id INTEGER,
    text TEXT,
    date INTEGER
)
""")

conn.commit()

# =====================================================
# TEMP
# =====================================================

waiting_rep = {}

# =====================================================
# REGISTER
# =====================================================

def register_user(user):

    cursor.execute("""
    SELECT * FROM users
    WHERE user_id=?
    """, (user.id,))

    if cursor.fetchone():
        return

    fake_id = str(random.randint(
        100000,
        999999
    ))

    cursor.execute("""
    INSERT INTO users
    VALUES(?,?,?,?)
    """, (
        user.id,
        fake_id,
        user.username or "none",
        int(time.time())
    ))

    conn.commit()

# =====================================================
# PHOTO
# =====================================================

def get_photo(user_id):

    try:

        photos = bot.get_user_profile_photos(
            user_id
        )

        if photos.total_count == 0:
            return None

        return photos.photos[0][-1].file_id

    except:
        return None

# =====================================================
# STATUS
# =====================================================

def get_status(user_id,total):

    cursor.execute("""
    SELECT reg_date FROM users
    WHERE user_id=?
    """, (user_id,))

    reg = cursor.fetchone()[0]

    weeks = (
        int(time.time()) - reg
    ) / 604800

    if total >= 160 and weeks >= 7:
        return "👑 Эксперт"

    elif total >= 110 and weeks >= 5:
        return "🏆 Мастер"

    elif total >= 55 and weeks >= 3:
        return "⭐ Средний"

    return "🔰 Новичок"

# =====================================================
# PROFILE
# =====================================================

def profile(user_id):

    cursor.execute("""
    SELECT * FROM users
    WHERE user_id=?
    """, (user_id,))

    data = cursor.fetchone()

    if not data:
        return None,None

    cursor.execute("""
    SELECT COUNT(*) FROM reps
    WHERE to_user=?
    AND rep_type='positive'
    """, (user_id,))

    pos = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM reps
    WHERE to_user=?
    AND rep_type='negative'
    """, (user_id,))

    neg = cursor.fetchone()[0]

    total = pos + neg

    if total == 0:

        pos_percent = 0
        neg_percent = 0

    else:

        pos_percent = round(
            pos / total * 100
        )

        neg_percent = round(
            neg / total * 100
        )

    status = get_status(
        user_id,
        total
    )

    # BAN

    cursor.execute("""
    SELECT * FROM bans
    WHERE user_id=?
    """, (user_id,))

    ban = cursor.fetchone()

    blocked = ""

    if ban:

        blocked = f"""

🚫 <b>Заблокирован</b>

💬 Причина:
{ban[1]}
"""

    text = f"""
<blockquote>
👤 @{data[2]}

🆔 <code>{data[1]}</code>

{blocked}

━━━━━━━━━━

⭐ Репутация: {total}

🟢 Положительный:
{pos_percent}%

🔴 Отрицательный:
{neg_percent}%

━━━━━━━━━━

📊 Статус:
{status}
</blockquote>
"""

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "📂 Отзывы",
            callback_data=f"reviews_{user_id}"
        )
    )

    return text,markup

# =====================================================
# MENU
# =====================================================

def menu():

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "👤 Моя репутация",
            callback_data="my_profile"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🏆 Топ репутации",
            callback_data="top_rep"
        )
    )

    return markup

# =====================================================
# START
# =====================================================

@bot.message_handler(commands=['start'])
def start(message):

    register_user(
        message.from_user
    )

    cursor.execute("""
    SELECT * FROM bans
    WHERE user_id=?
    """, (
        message.from_user.id,
    ))

    if cursor.fetchone():

        bot.send_message(
            message.chat.id,
            """
🚫 Вы заблокированы

Обратитесь к администрации.
"""
        )

        return

    text = """
<blockquote>
👋 Здравствуйте

Добро пожаловать
в систему репутации.
</blockquote>
"""

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=menu()
    )

# =====================================================
# CALLBACKS
# =====================================================

@bot.callback_query_handler(
    func=lambda c:
    c.data == "my_profile"
)
def my_profile(call):

    text,markup = profile(
        call.from_user.id
    )

    photo = get_photo(
        call.from_user.id
    )

    if photo:

        bot.send_photo(
            call.message.chat.id,
            photo,
            caption=text,
            reply_markup=markup
        )

    else:

        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=markup
        )

# =====================================================
# TOP
# =====================================================

@bot.callback_query_handler(
    func=lambda c:
    c.data == "top_rep"
)
def top_rep(call):

    cursor.execute("""
    SELECT to_user,
    COUNT(*) as total
    FROM reps
    WHERE date > ?
    GROUP BY to_user
    ORDER BY total DESC
    LIMIT 10
    """, (
        int(time.time()) - 86400,
    ))

    top = cursor.fetchall()

    if not top:

        bot.answer_callback_query(
            call.id,
            "Нет отзывов"
        )

        return

    text = "<blockquote>🏆 Топ за сегодня\n\n"

    place = 1

    for user in top:

        cursor.execute("""
        SELECT username
        FROM users
        WHERE user_id=?
        """, (user[0],))

        name = cursor.fetchone()

        if not name:
            continue

        text += f"""
{place}. @{name[0]} — {user[1]} REP
"""

        place += 1

    text += "</blockquote>"

    bot.send_message(
        call.message.chat.id,
        text
    )

# =====================================================
# PROFILE COMMAND
# =====================================================

@bot.message_handler(commands=['и'])
def info(message):

    args = message.text.split()

    if len(args) != 2:

        bot.reply_to(
            message,
            "❌ /и username"
        )

        return

    username = args[1].replace(
        "@",
        ""
    )

    cursor.execute("""
    SELECT * FROM users
    WHERE LOWER(username)=LOWER(?)
    """, (username,))

    data = cursor.fetchone()

    if not data:

        bot.reply_to(
            message,
            "❌ Такого пользователя нет"
        )

        return

    text,markup = profile(
        data[0]
    )

    photo = get_photo(
        data[0]
    )

    if photo:

        bot.send_photo(
            message.chat.id,
            photo,
            caption=text,
            reply_markup=markup
        )

# =====================================================
# TOP COMMAND
# =====================================================

@bot.message_handler(commands=['т'])
def top_today(message):

    cursor.execute("""
    SELECT to_user,
    COUNT(*) as total
    FROM reps
    WHERE date > ?
    GROUP BY to_user
    ORDER BY total DESC
    LIMIT 10
    """, (
        int(time.time()) - 86400,
    ))

    top = cursor.fetchall()

    text = "<blockquote>🏆 Топ за сегодня\n\n"

    place = 1

    for user in top:

        cursor.execute("""
        SELECT username
        FROM users
        WHERE user_id=?
        """, (user[0],))

        name = cursor.fetchone()

        if not name:
            continue

        text += f"""
{place}. @{name[0]} — {user[1]} REP
"""

        place += 1

    text += "</blockquote>"

    bot.send_message(
        message.chat.id,
        text
    )

# =====================================================
# REP COMMAND
# =====================================================

@bot.message_handler(
    func=lambda m:
    m.text and (
        m.text.lower().startswith("+реп")
        or
        m.text.lower().startswith("-реп")
        or
        m.text.lower().startswith("+rep")
        or
        m.text.lower().startswith("-rep")
    )
)
def rep_command(message):

    args = message.text.split()

    if len(args) < 3:

        bot.reply_to(
            message,
            "❌ +реп @user текст"
        )

        return

    username = args[1].replace(
        "@",
        ""
    )

    reason = " ".join(args[2:])

    cursor.execute("""
    SELECT * FROM users
    WHERE LOWER(username)=LOWER(?)
    """, (username,))

    user = cursor.fetchone()

    if not user:

        bot.reply_to(
            message,
            "❌ Пользователь не найден"
        )

        return

    # LIMIT 8

    cursor.execute("""
    SELECT COUNT(*) FROM reps
    WHERE to_user=?
    AND date > ?
    """, (
        user[0],
        int(time.time()) - 86400
    ))

    if cursor.fetchone()[0] >= 8:

        bot.reply_to(
            message,
            "❌ Лимит отзывов"
        )

        return

    waiting_rep[
        message.from_user.id
    ] = {
        "target": user[0],
        "reason": reason,
        "type":
        "positive"
        if "+" in message.text
        else "negative"
    }

    bot.reply_to(
        message,
        """
📷 Приложите скриншот

Без скриншота
отзыв не сохранится.
"""
    )

# =====================================================
# PHOTO REP
# =====================================================

@bot.message_handler(
    content_types=['photo']
)
def rep_photo(message):

    if message.from_user.id not in waiting_rep:
        return

    data = waiting_rep[
        message.from_user.id
    ]

    cursor.execute("""
    INSERT INTO reps(
        from_user,
        to_user,
        rep_type,
        reason,
        photo,
        date
    )
    VALUES(?,?,?,?,?,?)
    """, (
        message.from_user.id,
        data["target"],
        data["type"],
        data["reason"],
        message.photo[-1].file_id,
        int(time.time())
    ))

    conn.commit()

    del waiting_rep[
        message.from_user.id
    ]

    emoji = (
        "🟢"
        if data["type"] == "positive"
        else "🔴"
    )

    bot.reply_to(
        message,
        f"{emoji} Репутация сохранена"
    )

    try:

        sender = (
            message.from_user.username
            or
            "unknown"
        )

        bot.send_message(
            data["target"],
            f"""
<blockquote>
{emoji} Вам отправили REP

👤 @{sender}

💬 {data["reason"]}
</blockquote>
"""
        )

    except:
        pass

# =====================================================
# REVIEWS
# =====================================================

@bot.callback_query_handler(
    func=lambda c:
    c.data.startswith("reviews_")
)
def reviews(call):

    user_id = int(
        call.data.split("_")[1]
    )

    cursor.execute("""
    SELECT * FROM reps
    WHERE to_user=?
    ORDER BY id DESC
    LIMIT 10
    """, (user_id,))

    reps = cursor.fetchall()

    if not reps:

        bot.answer_callback_query(
            call.id,
            "Нет отзывов"
        )

        return

    for rep in reps:

        cursor.execute("""
        SELECT username
        FROM users
        WHERE user_id=?
        """, (rep[1],))

        sender = cursor.fetchone()

        sender_name = (
            sender[0]
            if sender
            else "unknown"
        )

        emoji = (
            "🟢"
            if rep[3] == "positive"
            else "🔴"
        )

        text = f"""
<blockquote>
{emoji} @{sender_name}

💬 {rep[4]}
</blockquote>
"""

        bot.send_photo(
            call.message.chat.id,
            rep[5],
            caption=text
        )

# =====================================================
# REPORT
# =====================================================

@bot.message_handler(commands=['report'])
def report(message):

    args = message.text.split()

    if len(args) < 3:

        bot.reply_to(
            message,
            "❌ /report @user причина"
        )

        return

    username = args[1].replace(
        "@",
        ""
    )

    reason = " ".join(args[2:])

    cursor.execute("""
    SELECT * FROM users
    WHERE LOWER(username)=LOWER(?)
    """, (username,))

    user = cursor.fetchone()

    if not user:

        bot.reply_to(
            message,
            "❌ Пользователь не найден"
        )

        return

    cursor.execute("""
    INSERT INTO reports(
        from_user,
        target_user,
        reason
    )
    VALUES(?,?,?)
    """, (
        message.from_user.id,
        user[0],
        reason
    ))

    conn.commit()

    bot.reply_to(
        message,
        "✅ Жалоба отправлена"
    )

    try:

        bot.send_message(
            ADMIN_ID,
            f"""
🚨 REPORT

👤 @{username}

💬 {reason}
"""
        )

    except:
        pass

# =====================================================
# BAN
# =====================================================

@bot.message_handler(commands=['ban'])
def ban(message):

    if message.from_user.id != ADMIN_ID:

        bot.reply_to(
            message,
            """
❌ Недостаточно ранга

Напишите администратору.
"""
        )

        return

    args = message.text.split()

    if len(args) < 3:
        return

    username = args[1].replace(
        "@",
        ""
    )

    reason = " ".join(args[2:])

    cursor.execute("""
    SELECT * FROM users
    WHERE LOWER(username)=LOWER(?)
    """, (username,))

    user = cursor.fetchone()

    if not user:
        return

    cursor.execute("""
    INSERT OR REPLACE INTO bans
    VALUES(?,?)
    """, (
        user[0],
        reason
    ))

    conn.commit()

    bot.reply_to(
        message,
        "🚫 Пользователь заблокирован"
    )

    try:

        bot.send_message(
            user[0],
            f"""
🚫 Вы были заблокированы

💬 Причина:
{reason}
"""
        )

    except:
        pass

# =====================================================
# UNBAN
# =====================================================

@bot.message_handler(commands=['unban'])
def unban(message):

    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()

    if len(args) != 2:
        return

    username = args[1].replace(
        "@",
        ""
    )

    cursor.execute("""
    SELECT * FROM users
    WHERE LOWER(username)=LOWER(?)
    """, (username,))

    user = cursor.fetchone()

    if not user:
        return

    cursor.execute("""
    DELETE FROM bans
    WHERE user_id=?
    """, (user[0],))

    conn.commit()

    bot.reply_to(
        message,
        "✅ Пользователь разбанен"
    )

# =====================================================
# MUTE
# =====================================================

@bot.message_handler(commands=['mute'])
def mute(message):

    if message.from_user.id != ADMIN_ID:

        bot.reply_to(
            message,
            "❌ Недостаточно ранга"
        )

        return

    args = message.text.split()

    if len(args) < 4:
        return

    username = args[1].replace(
        "@",
        ""
    )

    mute_time = int(args[2])

    reason = " ".join(args[3:])

    cursor.execute("""
    SELECT * FROM users
    WHERE LOWER(username)=LOWER(?)
    """, (username,))

    user = cursor.fetchone()

    if not user:
        return

    until = int(time.time()) + mute_time * 60

    cursor.execute("""
    INSERT OR REPLACE INTO mutes
    VALUES(?,?,?)
    """, (
        user[0],
        until,
        reason
    ))

    conn.commit()

    bot.reply_to(
        message,
        "🔇 Пользователь замучен"
    )

# =====================================================
# ANTI SPAM
# =====================================================

@bot.message_handler(func=lambda m: True)
def spam(message):

    cursor.execute("""
    SELECT * FROM antispam
    WHERE user_id=?
    ORDER BY date DESC
    LIMIT 1
    """, (message.from_user.id,))

    last = cursor.fetchone()

    if last:

        if (
            last[1].lower()
            ==
            message.text.lower()
        ):

            until = int(time.time()) + 600

            cursor.execute("""
            INSERT OR REPLACE INTO mutes
            VALUES(?,?,?)
            """, (
                message.from_user.id,
                until,
                "Flood"
            ))

            conn.commit()

            bot.reply_to(
                message,
                "🔇 Мут 10 минут за flood"
            )

            return

    cursor.execute("""
    INSERT INTO antispam
    VALUES(?,?,?)
    """, (
        message.from_user.id,
        message.text,
        int(time.time())
    ))

    conn.commit()

# =====================================================
# RUN
# =====================================================

print("BOT STARTED")

while True:

    try:

        bot.infinity_polling(
            timeout=60,
            long_polling_timeout=60
        )

    except Exception as e:

        print(e)

        time.sleep(5)
