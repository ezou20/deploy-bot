from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os

from langchain.agents import Tool
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain import OpenAI
from langchain.agents import initialize_agent

from llama_index import GPTSimpleVectorIndex

# Global variables
SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']
SLACK_APP_TOKEN = os.environ['SLACK_APP_TOKEN']

# this is our bot's ID
slack_bot_id = 'U051QHPFKKP'
# magic emoji that indicates the bot should respond in a thread
emoji = 'heart_hands'
app = App(token=SLACK_BOT_TOKEN)

# @app.message("hello")
# def message_hello(message, say):
#     result = agent_chain.run("this is a test")
#     print(result)
#     # say() sends a message to the channel where the event was triggered
#     say(
#         blocks=[
#             {
#                 "type": "section",
#                 "text": {"type": "mrkdwn", "text": f"Hey there <@{message['user']}>!"},
#                 "accessory": {
#                     "type": "button",
#                     "text": {"type": "plain_text", "text": "Click Me"},
#                     "action_id": "button_click"
#                 }
#             }
#         ],
#         text=f"Hey there <@{message['user']}>!"
#     )

# @app.action("button_click")
# def action_button_click(body, ack, say):
#     # Acknowledge the action
#     # we could maybe link to the right doc here
#     ack()
#     say(f"<@{body['user']['id']}> clicked the button")

# Check the messages in a thread to see if the Support Bot was mentioned at all and creates a thread history for the LLM to consume
# Returns true if the bot was found
def check_messages_in_thread(client, channel_id, thread_ts):
    print("Looking at thread history")
    memory.clear()
    support_bot_mentioned = False
    conversation_replies = client.conversations_replies(
        channel=channel_id,
        ts=thread_ts
    )
    # print("conversation replies: ", parent_conversation_object)
    for message in conversation_replies['messages']:
        if slack_bot_id in message['text']:
            support_bot_mentioned = True
        if message['user'] == slack_bot_id:
            memory.chat_memory.add_ai_message(message['text'])
        else:
            memory.chat_memory.add_user_message(message['text'])

    return support_bot_mentioned

@app.event("app_mention")
def handle_app_mention(body, client, logger):
    logger.info(body)

@app.event("message")
def handle_app_message_events(body, client, message, say, logger):
    logger.info(body)
    text = body['event']['text']
    thread = body['event']['ts']
    if 'thread_ts' in body['event']:
        thread = body['event']['thread_ts']
    channel_id = body['event']['channel']

    print("*************************** Handling New Message ************************************")
    print("THIS IS THE TEXT: ", text)
    print("THREAD ID: ", thread)
    print("CHANNEL ID: ", channel_id)
    
    # see if the bot was mentioned in the parent thread -- we only want it to respond in threads where it was mentioned
    parent_conversation_object = client.conversations_history(
        channel=channel_id,
        inclusive=True,
        oldest=thread,
        limit=1
    )
    print("Parent Object: ", parent_conversation_object)
    parent_message = parent_conversation_object['messages'][0]
    
    # check if the parent message has a reaction that matches the magic emoji
    emoji_in_message = False
    if 'reactions' in parent_message:
        parent_message_reactions = parent_conversation_object['messages'][0]['reactions']
        for reaction in parent_message_reactions:
            if reaction['name'] == emoji:
                emoji_in_message = True

    support_bot_in_thread = check_messages_in_thread(client, channel_id, thread)

    if slack_bot_id in text or (support_bot_in_thread and emoji_in_message):
        print("Generating AI Response...")
        ai_response = agent_chain.run(text)
        response_message = f"{ai_response}" # Hey there <@{body['event']['user']}>! 
        # print("Memory: ", memory.chat_memory)
        # print(ai_response)
        # print("Body: ", body)
        # print(message)
        say(
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": response_message},
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Click Me"},
                        "action_id": "button_click"
                    }
                }
            ],
            text=response_message,
            thread_ts=thread
        )

if __name__ == "__main__":
    # initialize LLM
    index = GPTSimpleVectorIndex.load_from_disk('retool_docs_simple_index.json')
    tools = [
        Tool(
            name='retool_docs',
            func=lambda question: str(index.query(question)),
            description="Retool Documentation. Useful for answering questions about Retool. Includes best practices, reference API documnetation, how to guides, and reommendations.",
            return_direct=True
        ),
        Tool(
            name='intro_bot',
            func=lambda question: f"I am Retool's (emotional) Support AI bot! Ask me anything! If you want me to respond to all messages in this thread, react with :{emoji}: in the parent message of the thread.",
            description="This bot is used for introducing what it does. Use this tool for when someone asks about the bot and what it does.",
            return_direct=True
        )
    ]
    memory = ConversationBufferMemory(memory_key="chat_history")
    llm = OpenAI(model_name="gpt-4", temperature=0)
    agent_chain = initialize_agent(
        tools=tools,
        llm=llm,
        agent="conversational-react-description",
        memory=memory
    )

    # set up Slack app
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()