import base64
from flask import Flask, abort, jsonify, render_template, request, redirect, session, url_for, flash
from werkzeug.security import check_password_hash
from passlib.hash import sha256_crypt
import psycopg2
import os
from werkzeug.utils import secure_filename
import logging

app = Flask(__name__, static_url_path='/static')

app = Flask(__name__)
app.secret_key = '123'  

UPLOAD_FOLDER = 'static/photo'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

logging.basicConfig(filename='app.log', level=logging.DEBUG)

# Подключение к базе данных
def connect_db():
    con = psycopg2.connect(
        host = '127.0.0.1',
        database = 'rgr2',
        user = 'sofiya_prytkova_knowledge_base',
        password = '123',
        port = 5433
    )
    return con

def dbClose(cursor,connection):
    cursor.close()
    connection.close()

# Хеширование пароля
def hash_password(password):
    return sha256_crypt.encrypt(password)

# Проверка пароля
def verify_password(password, password_hash):
    return sha256_crypt.verify(password, password_hash)

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# Страница Регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Проверка пустых значений
        if not username or not password:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('register'))

        # CПроверка на наличие пользователя
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
                existing_user = cursor.fetchone()

        if existing_user:
            flash('Username already exists', 'error')
            return redirect(url_for('register'))

        # Хеширование
        hashed_password = sha256_crypt.hash(password)

        # Сохранение пароля и имени в бд
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, hashed_password))

        flash('Registration successful', 'success')
        return redirect(url_for('anketa'))

    return render_template('register.html')

# Страница входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Проверка наличия пустых значений
        if not username or not password:
            error_message = 'Заполните все поля'
            return render_template('login.html', error_message=error_message)

        # Поиск пользователя в базе данных
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
                user = cursor.fetchone()

        if user and sha256_crypt.verify(password, user[2] if user else None):
            # Устанавливаем пользователя в сессию
            session['user_id'] = user[0]  # Предполагаем, что user[0] - это id пользователя
            session['username'] = user[1]  # user[1] - это поле с именем пользователя
            # Перенаправляем на страницу glav
            return redirect(url_for('glav'))
        else:
            error_message = 'Неверный логин или пароль'
            return render_template('login.html', error_message=error_message)

    return render_template('login.html')

# Роут для главной страницы
@app.route('/glav')
def glav():
    # Проверка наличия пользователя в сессии (залогинен ли пользователь)
    if 'username' not in session:
        # Если пользователь не залогинен, перенаправить на страницу входа
        return redirect(url_for('login'))

    # Получение имени пользователя из сессии
    username = session.get('username')
    return render_template('glav.html', username=username)

# Страница анкеты
@app.route('/anketa', methods=['GET', 'POST'])
def anketa():
    if request.method == 'POST':
        try:
            username = request.form['username']
            age = request.form['age']
            gender = request.form['gender']
            search_gender = request.form['search_gender']
            about_me = request.form['about_me']
            photo_path = None  # Инициализация переменной перед использованием

            # Проверка наличия обязательных полей
            if not username or not age or not gender or not search_gender or not about_me:
                flash('Пожалуйста, заполните все обязательные поля', 'error')
                return redirect(url_for('anketa'))

            # Преобразуем значения полей в английский язык
            gender_translation = {'Мужчина': 'male', 'Женщина': 'female'}
            search_gender_translation = {'Мужчина': 'male', 'Женщина': 'female'}
            gender = gender_translation.get(gender, gender)
            search_gender = search_gender_translation.get(search_gender, search_gender)

            # Проверяем, что файл имеет разрешенное расширение
            allowed_extensions = {'jpg', 'jpeg', 'png'}
            if 'photo' in request.files:
                photo = request.files['photo']

                # Проверяем, что файл имеет разрешенное расширение
                if '.' in photo.filename and photo.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    # Создаем директорию, если она не существует
                    os.makedirs(os.path.abspath('static/photo'), exist_ok=True)

                    # Сохраняем файл фотографии в папку загрузки
                    relative_photo_path = os.path.join('static/photo', secure_filename(photo.filename))
                    photo.save(relative_photo_path)
                else:
                    flash('Недопустимое расширение файла фотографии', 'error')
                    return redirect(url_for('anketa'))

            # Добавим отладочную информацию для вывода в лог
            print(f"Received data: {username}, {age}, {gender}, {search_gender}, {about_me}, {relative_photo_path}")

            # Сохраняем данные анкеты в базе данных
            with connect_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO Questionary (username, age, gender, search_gender, about_me, photo)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (username, age, gender, search_gender, about_me, relative_photo_path))

            print("Data successfully inserted into the database")  # Добавим отладочную информацию
            flash('Данные анкеты успешно сохранены', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            # Добавим отладочную информацию для вывода в лог
            print(f"An error occurred: {e}")
            logging.error(f"Произошла ошибка при обработке формы анкеты: {e}")
            flash('Произошла ошибка при обработке формы анкеты', 'error')
            return redirect(url_for('anketa'))

    return render_template('anketa.html')


# Маршрут для выхода
@app.route('/logout')
def logout():
    # Проверка, залогинен ли пользователь
    if 'username' in session:
        # Удаляем пользователя из сессии
        session.pop('username', None)
        flash('Вы успешно вышли из аккаунта', 'success')
    else:
        flash('Вы не вошли в аккаунт', 'error')

    # Перенаправляем на главную страницу
    return redirect(url_for('index'))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Функция для обновления данных анкеты в базе данных
def update_anketa(username, new_age, new_gender, new_search_gender, new_about_me, photo_filename):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            # Проверяем, есть ли уже анкета для данного пользователя
            cursor.execute('SELECT * FROM Questionary WHERE username = %s', (username,))
            existing_anketa = cursor.fetchone()

            if existing_anketa:
                # Если анкета уже существует, обновляем данные
                cursor.execute('''
                    UPDATE Questionary 
                    SET age = %s, gender = %s, search_gender = %s, about_me = %s, photo = %s
                    WHERE username = %s
                ''', (new_age, new_gender, new_search_gender, new_about_me, photo_filename, username))
            else:
                # Если анкеты нет, добавляем новую
                cursor.execute('''
                    INSERT INTO Questionary (username, age, gender, search_gender, about_me, photo)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (username, new_age, new_gender, new_search_gender, new_about_me, photo_filename))

        conn.commit()


# Функция для получения текущих данных анкеты из базы данных
def get_anketa_data(username):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM Questionary WHERE username = %s', (username,))
            anketa_data = cursor.fetchone()

    return anketa_data

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_anketa_by_username(username):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM Questionary WHERE username = %s', (username,))
            return cursor.fetchone()


# Роут для редактирования анкеты
@app.route('/edit_anketa', methods=['GET', 'POST'])
def edit_anketa():
    # Проверка, залогинен ли пользователь
    if 'username' not in session:
        flash('Для доступа к этой странице войдите в аккаунт', 'error')
        return redirect(url_for('login'))

    username = session['username']

    if request.method == 'POST':
        # Получаем данные из формы
        new_age = request.form['new_age']
        new_gender = request.form['new_gender']
        new_search_gender = request.form['new_search_gender']
        new_about_me = request.form['new_about_me']

        # Проверяем, был ли отправлен файл фотографии
        if 'photo' in request.files:
            new_photo = request.files['photo']

            # Проверяем, что файл имеет разрешенное расширение
            allowed_extensions = {'jpg', 'jpeg', 'png'}
            if (
                '.' in new_photo.filename
                and new_photo.filename.rsplit('.', 1)[1].lower() in allowed_extensions
            ):
                # Сохраняем файл фотографии в папку загрузки
                filename = secure_filename(new_photo.filename)
                photo_path = os.path.join(os.path.abspath('static/photo'), secure_filename(filename))
                new_photo.save(photo_path)

                # Обновляем данные в базе данных, включая новый путь к фото
                update_anketa(username, new_age, new_gender, new_search_gender, new_about_me, photo_path)

                flash('Данные анкеты успешно обновлены', 'success')
                return redirect(url_for('glav'))
            else:
                flash('Недопустимое расширение файла фотографии', 'error')
                return redirect(url_for('edit_anketa'))

    # Если запрос GET, отображаем форму редактирования
    current_anketa = get_anketa_by_username(username)
    return render_template('edit_anketa.html', current_anketa=current_anketa)

# Функция для получения списка анкет из базы данных, за исключением текущего пользователя
def get_other_anketa_list(current_username, language='en'):
    # Выбираем соответствующие столбцы в зависимости от языка
    if language == 'en':
        columns = ['username', 'age', 'gender', 'about_me', 'photo']
    elif language == 'ru':
        columns = ['username_ru', 'age_ru', 'gender_ru', 'about_me_ru', 'photo_ru']
    else:
        # По умолчанию использовать английский
        columns = ['username', 'age', 'gender', 'about_me', 'photo']

    with connect_db() as conn:
        with conn.cursor() as cursor:
            # Составляем запрос, используя соответствующие столбцы
            query = f'''
                SELECT {', '.join(columns)}
                FROM questionary
                WHERE is_visible = TRUE
                    AND username != %s
                ORDER BY id
            '''
            cursor.execute(query, (current_username,))
            anketa_list = cursor.fetchall()

    return anketa_list

# Функция для установки статуса видимости анкеты
def set_anketa_visibility(username, is_visible):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute('UPDATE questionary SET is_visible = %s WHERE username = %s', (is_visible, username))
        conn.commit()

# Роут для скрытия анкеты
@app.route('/hide_anketa', methods=['GET', 'POST'])
def hide_anketa():
    # Проверка, залогинен ли пользователь
    if 'username' not in session:
        flash('Для доступа к этой странице войдите в аккаунт', 'error')
        return redirect(url_for('login'))

    username = session['username']

    if request.method == 'POST':
        # Логика изменения статуса видимости анкеты
        set_anketa_visibility(username, False)  # Устанавливаем статус видимости в False
        flash('Анкета успешно скрыта', 'success')
        return redirect(url_for('glav'))

    return render_template('hide_anketa.html', username=username)

def get_filtered_anketa_list(username, search_age=None, search_gender=None, offset=0, limit=3):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            query = """
                SELECT username, age, gender, about_me, photo
                FROM questionary
                WHERE username != %s AND is_visible = true
                    AND (%s IS NULL OR age = %s)
                    AND (%s IS NULL OR gender = %s)
                ORDER BY id
                OFFSET %s LIMIT %s
            """
            print(f"Query: {query}")
            print(f"Parameters: {username}, {search_age}, {search_age}, {search_gender}, {search_gender}, {offset}, {limit}")
            
            cursor.execute(query, (username, search_age, search_age, search_gender, search_gender, offset, limit))
            anketa_list = cursor.fetchall()
            print(f"Result: {anketa_list}")
    return anketa_list

# Роут для просмотра анкет
@app.route('/view_anketa', methods=['GET'])
def view_anketa():
    # Проверка, залогинен ли пользователь
    if 'username' not in session:
        flash('Для доступа к этой странице войдите в аккаунт', 'error')
        return redirect(url_for('login'))

    username = session['username']
    offset = int(request.args.get('offset', 0))
    limit = 3

    # Получаем список анкет из базы данных
    anketa_list = get_filtered_anketa_list(username, offset=offset, limit=limit)

    return render_template('view_other_anketa.html', anketa_list=anketa_list, offset=offset, limit=limit)

# Роут для обработки формы фильтрации и загрузки следующих анкет
@app.route('/filter_anketa', methods=['POST'])
def filter_anketa():
    # Проверка, залогинен ли пользователь
    if 'username' not in session:
        flash('Для доступа к этой странице войдите в аккаунт', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Обработка данных формы и выполнение фильтрации
        search_gender = request.form['search_gender']
        search_age = request.form['search_age']

        # Map Russian gender values to English
        gender_mapping = {'Мужчина': 'Male', 'Женщина': 'Female'}
        search_gender_en = gender_mapping.get(search_gender, search_gender)

        username = session['username']
        offset = 0
        limit = 3

        # Получение списка анкет с учетом фильтров
        anketa_list = get_filtered_anketa_list(username, search_age=search_age, search_gender=search_gender_en, offset=offset, limit=limit)

        return render_template('view_other_anketa.html', anketa_list=anketa_list, offset=offset, limit=limit)
    else:
        # Возвращение ошибки, если получен GET-запрос
        return abort(400)

# Функция для удаления пользователя из базы данных
def delete_user(username):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            # Удаление пользователя из таблицы users
            cursor.execute('DELETE FROM users WHERE username = %s', (username,))

            # Удаление связанных данных из других таблиц, например, questionary
            cursor.execute('DELETE FROM questionary WHERE username = %s', (username,))
            # Добавьте другие таблицы, если необходимо

# Роут для удаления аккаунта
@app.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
    # Проверка, залогинен ли пользователь
    if 'username' not in session:
        flash('Для доступа к этой странице войдите в аккаунт', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Получаем имя пользователя из сессии
        username = session['username']

        # Удаление пользователя из базы данных
        delete_user(username)

        # Очистка сессии и перенаправление на главную страницу
        session.clear()
        flash('Ваш аккаунт успешно удален', 'success')
        return redirect(url_for('index'))

    return render_template('delete_account.html')  

if __name__ == '__main__':
    app.run(debug=True)
