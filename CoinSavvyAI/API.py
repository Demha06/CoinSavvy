import requests


def test_api(query):
    url = 'http://127.0.0.1:5000/query'  # Update with your API URL
    data = {'query': query}
    response = requests.post(url, json=data)

    if response.status_code == 200:
        result = response.json()
        return result['response']
    else:
        return f"Error: {response.status_code}"


#
while True:
    query = input("User: ")
    if query.lower() == 'exit':
        break
    response = test_api(query)
    print("Response:", response)


# from langchain.agents import load_tools
# from langchain.agents import initialize_agent
# from langchain_openai import OpenAI, ChatOpenAI
#
# import os
#
# os.environ['OPENAI_API_KEY'] = "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"
# os.environ['SERPAPI_API_KEY'] = "06066c87d3fa649ee744e8e7984f5d8f38616b313c3e1d25b616ddef05d3c8e5"
#
# llm = ChatOpenAI(temperature=0.6)
# tool_names = ["serpapi"]
# tools = load_tools(tool_names)
# agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)
# agent.run("how would i include serp api feature into my tools so that finance ai via langchain may access the internet for real time"
#           "information on finance. Is there a way to pass parameters to give instruction to the tool using serp api. Give me the details "
#           "on how to vividly do that")



# @csrf_exempt
# def whatsapp_bot(request):
#     if request.method == 'POST':
#         incoming_message = request.POST['Body'].strip().upper()
#         user_phone_number = request.POST['From']
#         user, created = User.objects.get_or_create(phone_number=user_phone_number)
#
#         response = MessagingResponse()
#         msg = response.message()
#
#         if created:  # If it's a new user, prompt for username
#             msg.body("Welcome to CoinSavvy!😎\nPlease enter your username:")
#             user.save()  # Save the new user
#
#         if incoming_message.lower() == 'exit':  # Check for exit command
#             return HttpResponse(str(response), content_type='application/xml')
#
#         query_response = ai_test_api(incoming_message)
#         msg.body(query_response)
#
#         return HttpResponse(str(response), content_type='application/xml')
