import random
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Subject, Ticket

app = Flask(__name__)
app.config['SECRET_KEY'] = "I_CAME-I_SAW-I_CONQUERED"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exam_master.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Пожалуйста, войдите, чтобы получить доступ."


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует.')
            return redirect(url_for('register'))

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('index'))
    return render_template('auth.html', action='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))

        flash('Неверное имя пользователя или пароль.')
    return render_template('auth.html', action='login')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        subject_title = request.form.get('title')
        if subject_title:
            new_sub = Subject(title=subject_title.lower(), user_id=current_user.id)
            db.session.add(new_sub)
            db.session.commit()
            return redirect(url_for('index'))

    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', subjects=subjects)

@app.route('/upload/<int:sub_id>', methods=['POST'])
@login_required
def upload(sub_id):
    file = request.files.get('file')
    if file and file.filename and file.filename.endswith('.txt'):
        content = file.read().decode('utf-8')
        tickets_to_add = []
        for line in content.strip().split('\n'):
            line = line.strip()
            if not line or ';' not in line:
                continue
            q, a = line.split(';', 1)
            tickets_to_add.append(Ticket(question=q.strip(), answer=a.strip(), subject_id=sub_id))

        if tickets_to_add:
            db.session.bulk_save_objects(tickets_to_add)
            db.session.commit()
            flash(f'Успешно загружено {len(tickets_to_add)} билетов!')
    else:
        flash('Ошибка: файл должен быть в формате .txt')

    return redirect(url_for('index'))

@app.route('/delete_subject/<int:sub_id>', methods=['POST'])
@login_required
def delete_subject(sub_id):
    subject = Subject.query.get_or_404(sub_id)
    if subject.user_id != current_user.id:
        flash("У вас нет прав на это действие.")
        return redirect(url_for('index'))

    db.session.delete(subject)
    db.session.commit()
    flash(f'Предмет "{subject.title}" удален.')
    return redirect(url_for('index'))

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    user = User.query.get(current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash('Ваш аккаунт и все данные были безвозвратно удалены.')
    return redirect(url_for('register'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
