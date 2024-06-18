from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.messaging_response import MessagingResponse
import json
from .models import User
import requests
from requests.auth import HTTPBasicAuth
from pydub import AudioSegment
import os
from tempfile import NamedTemporaryFile
import speech_recognition as sr

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


def ai_test_api(query):
    url = 'http://127.0.0.1:5000/query'  # Update with your API URL
    data = {'query': query}
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
        result = response.json()
        return result['response']
    except Exception as e:
        return f"Error: {str(e)}"


def transcribe_audio(audio_content):
    with NamedTemporaryFile(suffix=".ogg") as temp_ogg:
        temp_ogg.write(audio_content)
        temp_ogg.flush()  # Ensure content is written
        os.fsync(temp_ogg.fileno())  # Ensure written to disk
        temp_ogg.seek(0)  # Go to the start of the file

        with NamedTemporaryFile(suffix='.wav') as temp_wav:
            audio = AudioSegment.from_ogg(temp_ogg.name)
            audio.export(temp_wav.name, format="wav")
            temp_wav.seek(0)  # Ensure the pointer is at the start

            r = sr.Recognizer()
            with sr.AudioFile(temp_wav.name) as source:
                audio_data = r.record(source)
                text = r.recognize_google(audio_data)
                return text


@csrf_exempt
def whatsapp_bot(request):
    if request.method == 'POST':
        user_phone_number = request.POST.get('From')
        # Assuming a get_or_create method for User and other relevant models is defined
        user, created = User.objects.get_or_create(phone_number=user_phone_number)

        response = MessagingResponse()
        msg = response.message()

        if created:
            msg.body("Welcome! Please enter your username:")
            user.save()
            return HttpResponse(str(response), content_type='application/xml')

        # Process audio message if available
        if request.POST.get('NumMedia') != '0':
            audio_url = request.POST.get('MediaUrl0')

            # Your Twilio Account SID and Auth Token
            account_sid = 'AC84253ea16f993102581fd07dd2cc0e98'
            auth_token = '9df81d9a1fae663f6a705f54915097e9'

            # Fetch the audio content with proper authentication
            audio_response = requests.get(audio_url, auth=HTTPBasicAuth(account_sid, auth_token))

            if audio_response.status_code == 200:
                audio_content = audio_response.content
                incoming_message = transcribe_audio(audio_content)
            else:
                print("Failed to download audio file. Status code:", audio_response.status_code)
                msg.body("Failed to process your audio message. Please try again.")
                return HttpResponse(str(response), content_type='application/xml')

        # Process text message
        else:
            incoming_message = request.POST.get('Body', '').strip().upper()

        if incoming_message.lower() == 'exit':
            # Handle an exit command from the user
            msg.body("Goodbye!")
            return HttpResponse(str(response), content_type='application/xml')

        # Use your API or logic for handling the incoming message
        query_response = ai_test_api(incoming_message)
        msg.body(query_response)

        return HttpResponse(str(response), content_type='application/xml')
    else:
        # Handle non-POST requests or return a simple error message
        return HttpResponse("Only POST requests are allowed.", status=405)


# Uncomment to run quiz (NB: Comment Csrf code from above)
# @csrf_exempt
# def whatsapp_bot(request):
#     if request.method == 'POST':
#         incoming_message = request.POST['Body'].strip().upper()
#         response = MessagingResponse()
#         msg = response.message()
#
#         user_phone_number = request.POST['From']
#         user, created = User.objects.get_or_create(phone_number=user_phone_number)
#
#         if created:  # If it's a new user, prompt for username
#             msg.body("Welcome to CoinSavvy!😎\nPlease enter your username:")
#             return HttpResponse(str(response), content_type='application/xml')
#
#         if not user.username:  # If user doesn't have a username yet
#             user.username = incoming_message
#             user.save()
#             topic_options = "\n".join([f"{idx}. {topic}" for idx, topic in enumerate(topics, start=1)])
#             msg.body(f"Hello {user.username}! Welcome to CoinSavvy!😎\nPlease select a topic:\n{topic_options}")
#             return HttpResponse(str(response), content_type='application/xml')
#
#         # If the user has a username, continue with topic selection or quiz
#         if incoming_message == "CHANGE":
#             user.topic = None
#             user.current_question_index = 0
#             user.score = 0
#             user.survey_response = None
#             user.save()
#             topic_options = "\n".join([f"{idx}. {topic}" for idx, topic in enumerate(topics, start=1)])
#             msg.body(f"Welcome back {user.username}!😎 Please select a new topic:\n{topic_options}")
#         elif user.topic is None:
#             try:
#                 topic_choice = int(incoming_message) - 1
#                 if 0 <= topic_choice < len(topics):
#                     user.topic = topics[topic_choice]
#                     user.current_question_index = 0
#                     user.score = 0
#                     user.survey_response = None
#                     user.save()
#
#                     dataset = load_questions()[user.topic]
#                     question_texts = ask_next_question(user, dataset)
#                     topic_intro = f"You have selected '{user.topic}'\n"
#                     question_texts.insert(0, topic_intro)
#                     for question_text in question_texts:
#                         msg.body(question_text)
#                 else:
#                     msg.body("Invalid topic selection.")
#             except ValueError:
#                 msg.body("Invalid input. Please enter a valid number.")
#         else:
#             if incoming_message in ["A", "B", "C", "D"]:
#                 user_answer = incoming_message
#                 response_msg = process_answer(user, user_answer)
#                 msg.body(response_msg)
#
#                 dataset = load_questions()[user.topic]
#                 if user.current_question_index < len(dataset):
#                     question_texts = ask_next_question(user, dataset)
#                     for question_text in question_texts:
#                         msg.body(question_text)
#                 else:
#                     if user.survey_response is None:
#                         final_score_msg = display_score(user.score, len(dataset))
#                         msg.body(
#                             f"You've completed the quiz for '{user.topic}'🥳!\n{final_score_msg}\nType 'CHANGE' to select a new topic\n")
#                         msg.body(ask_for_survey())
#                     else:
#                         msg.body(
#                             "You've completed the quiz for this topic! Feel free to type 'CHANGE' to select a new "
#                             "topic.")
#             elif incoming_message.isdigit() and user.survey_response is None:
#                 survey_choice = int(incoming_message)
#                 if 1 <= survey_choice <= 5:
#                     user.survey_response = survey_choice
#                     user.save()
#                     msg.body("Thank you for your feedback!")
#                 else:
#                     msg.body("Invalid survey response. Please enter a number between 1 and 5.")
#             else:
#                 msg.body("Invalid input. Please use appropriate response!")
#
#     return HttpResponse(str(response), content_type='application/xml')
