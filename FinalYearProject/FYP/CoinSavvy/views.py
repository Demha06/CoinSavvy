
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.messaging_response import MessagingResponse
import json
from .models import User

topics = [
    'Investments',
    'Loans and Debt',
    'Interest',
    'Banking Fees',
    'Identity Theft',
    'Risk Management',
    'Financial Planning and Goals'
]


def load_questions():
    with open('questions.json', 'r') as file:
        return json.load(file)


def display_score(correct, total):
    return f"Your current score is: {correct}/{total}"


def ask_next_question(user, questions):
    question_data = questions[user.current_question_index]
    question = question_data['question']
    options = question_data['options']

    question_str = f"{question}\n"
    for option_idx, option in enumerate(options, start=ord('A')):
        question_str += f"{chr(option_idx)}. {option}\n"

    return [f"Question {user.current_question_index + 1}/{len(questions)}:\n{question_str}"]


def process_answer(user, user_answer):
    if user.topic in topics:
        topic_idx = topics.index(user.topic)
        dataset = load_questions()[user.topic]

        if user.current_question_index < len(dataset):
            current_question = dataset[user.current_question_index]
            correct_option_idx = current_question['correct_option']
            correct_option = chr(correct_option_idx + ord('A'))

            if user_answer == correct_option:
                user.score += 1

            user.current_question_index += 1
            user.save()

            if user_answer == correct_option:
                return f"Correct🤩! {current_question.get('explanation', '')}"
            else:
                return f"Incorrect😔. The correct answer is {correct_option}.\n{current_question.get('explanation', '')}"
        else:
            return "You've answered all questions in this topic."
    else:
        return "Invalid topic."


def ask_for_survey():
    return "\n\nPlease rate your satisfaction with the topic:\n" \
           "1. Not Satisfied\n" \
           "2. Somewhat Satisfied\n" \
           "3. Neutral\n" \
           "4. Satisfied\n" \
           "5. Very Satisfied\n" \
           "Reply with the corresponding number."


@csrf_exempt
def whatsapp_bot(request):
    if request.method == 'POST':
        incoming_message = request.POST['Body'].strip().upper()
        response = MessagingResponse()
        msg = response.message()

        user_phone_number = request.POST['From']
        user, created = User.objects.get_or_create(phone_number=user_phone_number)

        if created:  # If it's a new user, prompt for username
            msg.body("Welcome to CoinSavvy!😎\nPlease enter your username:")
            return HttpResponse(str(response), content_type='application/xml')

        if not user.username:  # If user doesn't have a username yet
            user.username = incoming_message
            user.save()
            topic_options = "\n".join([f"{idx}. {topic}" for idx, topic in enumerate(topics, start=1)])
            msg.body(f"Hello {user.username}! Welcome to CoinSavvy!😎\nPlease select a topic:\n{topic_options}")
            return HttpResponse(str(response), content_type='application/xml')

        # If the user has a username, continue with topic selection or quiz
        if incoming_message == "CHANGE":
            user.topic = None
            user.current_question_index = 0
            user.score = 0
            user.survey_response = None
            user.save()
            topic_options = "\n".join([f"{idx}. {topic}" for idx, topic in enumerate(topics, start=1)])
            msg.body(f"Welcome back {user.username}!😎 Please select a new topic:\n{topic_options}")
        elif user.topic is None:
            try:
                topic_choice = int(incoming_message) - 1
                if 0 <= topic_choice < len(topics):
                    user.topic = topics[topic_choice]
                    user.current_question_index = 0
                    user.score = 0
                    user.survey_response = None
                    user.save()

                    dataset = load_questions()[user.topic]
                    question_texts = ask_next_question(user, dataset)
                    topic_intro = f"You have selected '{user.topic}'\n"
                    question_texts.insert(0, topic_intro)
                    for question_text in question_texts:
                        msg.body(question_text)
                else:
                    msg.body("Invalid topic selection.")
            except ValueError:
                msg.body("Invalid input. Please enter a valid number.")
        else:
            if incoming_message in ["A", "B", "C", "D"]:
                user_answer = incoming_message
                response_msg = process_answer(user, user_answer)
                msg.body(response_msg)

                dataset = load_questions()[user.topic]
                if user.current_question_index < len(dataset):
                    question_texts = ask_next_question(user, dataset)
                    for question_text in question_texts:
                        msg.body(question_text)
                else:
                    if user.survey_response is None:
                        final_score_msg = display_score(user.score, len(dataset))
                        msg.body(
                            f"You've completed the quiz for '{user.topic}'🥳!\n{final_score_msg}\nType 'CHANGE' to select a new topic\n")
                        msg.body(ask_for_survey())
                    else:
                        msg.body(
                            "You've completed the quiz for this topic! Feel free to type 'CHANGE' to select a new "
                            "topic.")
            elif incoming_message.isdigit() and user.survey_response is None:
                survey_choice = int(incoming_message)
                if 1 <= survey_choice <= 5:
                    user.survey_response = survey_choice
                    user.save()
                    msg.body("Thank you for your feedback!")
                else:
                    msg.body("Invalid survey response. Please enter a number between 1 and 5.")
            else:
                msg.body("Invalid input. Please use appropriate response!")

    return HttpResponse(str(response), content_type='application/xml')


