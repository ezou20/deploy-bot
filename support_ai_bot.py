from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os

from langchain.agents import Tool
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain import OpenAI
from langchain.agents import initialize_agent

from llama_index import GPTSimpleVectorIndex

SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']
SLACK_APP_TOKEN = os.environ['SLACK_APP_TOKEN']

app = App(token=SLACK_BOT_TOKEN)

@app.message("hello")
def message_hello(message, say):
    result = agent_chain.run("this is a test")
    print(result)
    # say() sends a message to the channel where the event was triggered
    say(
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Hey there <@{message['user']}>!"},
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Click Me"},
                    "action_id": "button_click"
                }
            }
        ],
        text=f"Hey there <@{message['user']}>!"
    )

@app.action("button_click")
def action_button_click(body, ack, say):
    # Acknowledge the action
    ack()
    say(f"<@{body['user']['id']}> clicked the button")

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)
    print("hi+")

@app.event("app_mention")
def handle_app_mention_events(body, message, say, logger):
    print("handling message")
    text = body['event']['text']
    result = agent_chain.run(text)
    print(result)
    print("Body: ", body)
    # print(message)
    say(
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Hey there <@{body['event']['user']}>! Here's your answer: {result}"},
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Click Me"},
                    "action_id": "button_click"
                }
            }
        ],
        text=f"Hey there !"
    )
    logger.info(body)

# @app.event("app_mention")
# async def handle_mentions(event, client, say):  # async function
#     api_response = await client.reactions_add(
#         channel=event["channel"],
#         timestamp=event["ts"],
#         name="eyes",
#     )
#     await say("What's up?")

if __name__ == "__main__":
    # initialize LLM
    index = GPTSimpleVectorIndex.load_from_disk('retool_docs_simple_index.json')
    tools = [
        Tool(
            name='retool_docs',
            func=lambda question: str(index.query(question)),
            description="Retool Documentation. Useful for answering questions about Retool. Includes best practices, reference API documnetation, how to guides, and reommendations.",
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