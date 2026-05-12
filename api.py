import re
import random
import difflib
from difflib import SequenceMatcher
from flask import Blueprint, request, jsonify
from models import db, Subject, Ticket

alice_bp = Blueprint('alice', __name__)

def build_alice_response(req, text, state, end_session=False):
    return jsonify({
        "version": req["version"],
        "session": req["session"],
        "response": {
            "text": text,
            "end_session": end_session
        },
        "session_state": state
    })

@alice_bp.route('/alice', methods=['POST'])
def alice_webhook():
    req = request.json
    state = req.get("state", {}).get("session", {})
    command = req['request']['command'].lower().strip()

    if req['session']['new']:
        return build_alice_response(req, "Привет! Я твой экзаменатор. Какой предмет будем повторять?", {})

    if command in ['другой предмет', 'сменить предмет', 'назад', 'стоп', 'все', 'хватит']:
        state = {}
        return build_alice_response(req, "Хорошо. Какой предмет выберем теперь?", state)

    if 'subject_id' not in state:
        subjects = Subject.query.all()
        subject_dict = {s.title.lower(): s for s in subjects}
        matches = difflib.get_close_matches(command, subject_dict.keys(), n=1, cutoff=0.6)

        if matches:
            subject = subject_dict[matches[0]]
            state['subject_id'] = subject.id
            return build_alice_response(req, f"Выбран предмет: {subject.title}. Скажи 'билет', чтобы начать.", state)
        return build_alice_response(req, "Не нашла такой предмет. Попробуй еще раз.", state)

    if 'current_ticket_id' in state:
        if command not in ['дальше', 'пропустить', 'не знаю', 'еще']:
            ticket = db.session.get(Ticket, state['current_ticket_id'])
            if ticket:
                user_ans = command.lower()
                correct_ans = ticket.answer.lower()
                user_numbers = re.findall(r'\d+', user_ans)
                correct_numbers = re.findall(r'\d+', correct_ans)
                is_correct = False

                if correct_numbers:
                    if any(num in user_numbers for num in correct_numbers):
                        is_correct = True

                if not is_correct:
                    similarity = SequenceMatcher(None, user_ans, correct_ans).ratio()
                    if similarity >= 0.65:
                        is_correct = True

                reply = "Верно!" if is_correct else f"Не совсем. Правильно: {ticket.answer}"
                state.pop('current_ticket_id')
                return build_alice_response(req, f"{reply}. Скажи 'дальше' для следующего вопроса.", state)
        state.pop('current_ticket_id')

    tickets = Ticket.query.filter_by(subject_id=state['subject_id']).all()
    if tickets:
        t = random.choice(tickets)
        state['current_ticket_id'] = t.id
        return build_alice_response(req, f"Вопрос: {t.question}", state)

    return build_alice_response(req, "В этом предмете нет билетов.", state)
