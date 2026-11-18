import streamlit as st 
from backend import chatbot,retrive_all_thread_id,conn
from langchain_core.messages import HumanMessage,AIMessage,ToolMessage
import uuid
import logging




logger = logging.getLogger(__name__)

# ***************************************  utility functions        ********************************************************************

# Use a mutable holder so the generator can set/modify it


def ai_only_stream():
    for message_chunk, metadata in chatbot.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=CONFIG,
        stream_mode="messages",
    ):
        # Lazily create & update the SAME status container when any tool runs
        if isinstance(message_chunk, ToolMessage):
            tool_name = getattr(message_chunk, "name", "tool")
            if status_holder["box"] is None:
                status_holder["box"] = st.status(
                    f"🔧 Using `{tool_name}` …", expanded=True
                )
            else:
                status_holder["box"].update(
                    label=f"🔧 Using `{tool_name}` …",
                    state="running",
                    expanded=True,
                )

        # Stream ONLY assistant tokens
        if isinstance(message_chunk, AIMessage):
            content = message_chunk.content

            if isinstance(content, str) and content:
                yield content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        if text:
                            yield text









# thread_id func
def generate_threaid():
      
    return str(uuid.uuid4())

#add threadid 

def add_thread(thread_id):
    if thread_id  not in st.session_state['chat_threads']:

        st.session_state['chat_threads'].append(thread_id) 


def reset_chat():
    thread_id = generate_threaid()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []


def load_conversation(thread_id):

    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})


  # Check if messages key exists in state values, return empty list if not
    return state.values.get('messages',[])


def clear_chat_history():
    st.session_state["thread_id"] = generate_threaid()
    st.session_state["message_history"] = []
    st.session_state["chat_threads"] = []
    


# visible thread at sidebar
def DisplayThread(thread_id):
    messages = load_conversation(thread_id)
    msg = []

    for message in messages:
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            continue

        content = message.content

        if isinstance(content, list):
            content = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )

        # Hide empty assistant tool-call messages
        if not isinstance(content, str) or not content.strip():
            continue

        msg.append({"role": role, "content": content})

    st.session_state["thread_id"] = thread_id
    st.session_state["message_history"] = msg

    st.session_state['thread_id'] = thread_id
    st.session_state['message_history'] = msg
    
   









# *****************************************  Intial setup   ******************************************************************

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_threaid()   


if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retrive_all_thread_id()

add_thread(st.session_state['thread_id'])



  




#******************************* sideBar UI *******************************

st.sidebar.title('LangGraph Chatbot')

if st.sidebar.button('New chat'):
     reset_chat()

     with st.chat_message('assistant'):
             st.text(" Hi! I am your AI assistant. How can I help you today?")

st.sidebar.header('My Conversations')


for thread_id in st.session_state['chat_threads'][::-1]:
    if st.sidebar.button(str(thread_id)):
        DisplayThread(thread_id)

        


if st.sidebar.button("restart"):
    
    conn.execute("DELETE FROM writes")
    conn.execute("DELETE FROM checkpoints")

    conn.commit()
    clear_chat_history()

    

       
        

#************************ Main UI ********************************************

CONFIG =  {"configurable" : {"thread_id" : st.session_state['thread_id']}}


for msg in st.session_state['message_history']:

    with st.chat_message(msg['role']):
        st.text(msg['content'])


user_input = st.chat_input('Type here')

if user_input:

    status_holder = {"box": None}
    
    

    st.session_state['message_history'].append({'role':'user' , 'content' : user_input})
    with st.chat_message('user'):
        st.text(user_input)

    
    with st.chat_message('assistant'):


        try:
            ai_message = st.write_stream(ai_only_stream())

            if status_holder["box"] is not None:
                status_holder["box"].update(
                    label="✅ Tool finished",
                    state="complete",
                    expanded=False,
                )

            st.session_state["message_history"].append({
                "role": "assistant",
                "content": ai_message,
            })

        except Exception:
            logger.exception("AI service request failed")
            st.error(
                "I couldn’t connect to the AI service. Please try again in a moment.",
                icon="⚠️",
            )