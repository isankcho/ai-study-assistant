import streamlit as st
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)
from ui.Page import Page
from ui.state import save_state_to_cache
from workflows.chatbot_workflow import ChatbotWorkflow


class ChatbotPage(Page):
    """UI for the chatbot page."""

    def __init__(self, chatbot_workflow: ChatbotWorkflow):
        self.chatbot_workflow = chatbot_workflow

    def render(self):
        st.title("Ask me anything!")
        for message in st.session_state.chatbot_messages:
            if isinstance(message, HumanMessage):
                with st.chat_message("user"):
                    st.markdown(message.content)
            elif isinstance(message, (AIMessage, ToolMessage)):
                with st.chat_message("assistant"):
                    st.markdown(message.content)

        if prompt := st.chat_input(
            "Ask anything", disabled=st.session_state.chatbot_turn != "human"
        ):
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.chatbot_messages.append(HumanMessage(content=prompt))
            st.session_state.chatbot_turn = "ai"
            save_state_to_cache()
            st.rerun()

        if st.session_state.chatbot_turn == "ai":
            with st.chat_message("assistant"):
                with st.spinner("Thinking...", show_time=True):
                    bot_message = None
                    try:
                        response = self.chatbot_workflow.run(
                            {"messages": st.session_state.chatbot_messages},
                        )
                        bot_message = response["messages"][-1]
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
                        bot_message = AIMessage(content="An error occurred.")
                    finally:
                        st.session_state.chatbot_messages.append(bot_message)
                        st.session_state.chatbot_turn = "human"
                        save_state_to_cache()
                        st.rerun()
