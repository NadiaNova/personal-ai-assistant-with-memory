"""
Streamlit application for the Personal AI Assistant / RAG Chatbot
"""

import task_manager
from datetime import date, time, datetime

import streamlit as st
import logging

from chatbot import RAGChatbot
import config
import utils


# Setup logging
utils.setup_logging()
logger = logging.getLogger(__name__)


def initialize_session_state():
    """Initialize Streamlit session state variables."""

    if "chatbot" not in st.session_state:
        st.session_state.chatbot = RAGChatbot()
        logger.info("Initialized new chatbot instance")

    if config.SESSION_MESSAGES not in st.session_state:
        st.session_state[config.SESSION_MESSAGES] = []


def display_chat_messages():
    """Display chat messages from history."""

    for message in st.session_state[config.SESSION_MESSAGES]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def apply_custom_styles():
    """Apply the visual theme for the assistant workspace."""

    st.markdown(
        """
        <style>
        .block-container {
           max-width: 1120px;
           padding-top: 3rem;
           padding-bottom: 3rem;
        }
        .workspace-header {
            max-width: 100%;
            min-width: 0;
        }
        .workspace-header h1 {
            font-size: clamp(1.75rem, 5vw, 2.75rem);
            line-height: 1.15;
            overflow-wrap: break-word;
        }
        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(148, 163, 184, 0.14);
        }
        [data-testid="stChatMessage"] {
            border: 1px solid rgba(148, 163, 184, 0.12);
            border-radius: 16px;
            padding: 1rem 1.15rem;
            margin-bottom: 0.75rem;
        }       

        [data-testid="stChatInput"] {
           border-color: rgba(0, 212, 170, 0.42);
        }

        div.stButton > button {
            border-radius: 10px;
            min-height: 2.65rem;
        }
        .workspace-header .workspace-eyebrow {
            display: block;
            width: 100%;
            max-width: 100%;
            min-width: 0;
            box-sizing: border-box;
            white-space: normal;
            overflow-wrap: break-word;
            word-break: normal;
            color: #00D4AA;
            font-size: clamp(0.65rem, 2.8vw, 0.76rem);
            font-weight: 700;
            letter-spacing: 0.04em;
            line-height: 1.5;
            margin-bottom: 0.55rem;
        }
        .workspace-subtitle {
            color: #A9BCB8;
            font-size: 1.02rem;
            line-height: 1.5;
            margin-top: -0.45rem;
        }
        .workspace-status {
            display: inline-flex;
            max-width: 100%;
            border: 1px solid rgba(0, 212, 170, 0.3);
            border-radius: 999px;
            color: #00D4AA;
            font-size: 0.82rem;
            line-height: 1.4;
            padding: 0.4rem 0.75rem;
            margin-top: 0.6rem;
        }
        
        /* Developer credit - bottom right corner */
        .developer-credit {
            position: fixed;
            bottom: 12px;
            right: 20px;
            z-index: 999999;
            font-size: 12px;
            color: #A9BCB8;
            background: rgba(15, 23, 42, 0.90);
            padding: 7px 12px;
            border: 1px solid rgba(0, 212, 170, 0.25);
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }

        .developer-credit span {
            color: #00D4AA;
            font-weight: 700;
       }
        </style>
        """,
        unsafe_allow_html=True,
    )


# Added ny Nova dated 12-10-2026 for reminders, to do list

def render_chat_tab(chatbot):
    """Keep the chat input above the conversation."""

    # Keep the input at the top, before the conversation history.
    prompt = st.chat_input(
        "Ask me anything, or ask about your saved memories...",
        key="main_chat_input",
    )

    # Show all previous messages below the input.
    display_chat_messages()

    if prompt:
        st.session_state[config.SESSION_MESSAGES].append(
            {"role": "user", "content": prompt}
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = chatbot.chat(prompt)
                answer = response.get(
                    "result", "Sorry, I could not generate a response."
                )

            if isinstance(answer, list):
                answer = "".join(
                    item.get("text", "")
                    for item in answer
                    if isinstance(item, dict)
                )

            st.markdown(answer)

            sources = response.get("source_documents", [])
            if sources:
                with st.expander("📚 Sources"):
                    st.markdown(utils.format_sources(sources))

        st.session_state[config.SESSION_MESSAGES].append(
            {"role": "assistant", "content": answer}
        )

def render_tasks_tab():
    """Persistent tasks, due-date reminders, and notes."""

    st.subheader("➕ Add a task")

    with st.form("add_task_form", clear_on_submit=True):
        task_title = st.text_input("Task title")
        set_due_date = st.checkbox("Set a due date and reminder")
        due_date = st.date_input("Due date", value=date.today())
        due_time = st.time_input("Due time", value=time(9, 0))

        submitted = st.form_submit_button("Save task", type="primary")

        if submitted:
            if not task_title.strip():
                st.error("Please enter a task title.")
            else:
                due_at = None
                if set_due_date:
                    due_at = datetime.combine(
                        due_date, due_time
                    ).isoformat(timespec="minutes")

                task_manager.add_task(task_title, due_at)
                st.success("Task saved.")
                st.rerun()

    st.divider()
    st.subheader("⏰ Scheduled reminders")

    reminders = task_manager.get_due_reminders()
    if reminders:
        for task in reminders:
            due_at = datetime.fromisoformat(task["due_at"])
            reminder = (
                f"**{task['title']}** — due "
                f"{due_at.strftime('%Y-%m-%d %H:%M')}"
            )
            if due_at <= datetime.now():
                st.warning(reminder)
            else:
                st.info(f"Upcoming: {reminder}")
    else:
        st.info("No scheduled reminders.")

    st.divider()
    st.subheader("📋 Your tasks")

    tasks = task_manager.get_tasks()
    if not tasks:
        st.caption("No tasks yet. Add your first task above.")

    for task in tasks:
        col1, col2, col3 = st.columns([0.12, 0.68, 0.20])

        with col1:
            is_done = st.checkbox(
                "Completed",
                value=bool(task["completed"]),
                key=f"task_done_{task['id']}",
                label_visibility="collapsed",
            )

        if is_done != bool(task["completed"]):
            task_manager.complete_task(task["id"], is_done)
            st.rerun()

        with col2:
            if task["completed"]:
                st.markdown(f"~~{task['title']}~~")
            else:
                st.markdown(f"**{task['title']}**")

            if task["due_at"]:
                st.caption(
                    f"Due: {task['due_at'].replace('T', ' ')}"
                )

        with col3:
            if st.button("Delete", key=f"delete_task_{task['id']}"):
                task_manager.delete_task(task["id"])
                st.rerun()


def render_notes_tab():
    """Display and manage saved notes."""

    st.subheader("📝 Notes")

    with st.form("add_note_form", clear_on_submit=True):
        note_title = st.text_input("Note title")
        note_content = st.text_area("Note content")
        save_note = st.form_submit_button("Save note")

        if save_note:
            if not note_title.strip() or not note_content.strip():
                st.error("Enter both a title and note content.")
            else:
                task_manager.add_note(note_title, note_content)
                st.success("Note saved.")
                st.rerun()

    for note in task_manager.get_notes():
        with st.expander(note["title"]):
            st.write(note["content"])
            st.caption(f"Created: {note['created_at']}")

            if st.button("Delete note", key=f"delete_note_{note['id']}"):
                task_manager.delete_note(note["id"])
                st.rerun()


def main():
    """Main Streamlit application."""

    # Configure page
    st.set_page_config(
        page_title=config.PAGE_TITLE,
        page_icon=config.PAGE_ICON,
        layout=config.PAGE_LAYOUT,
    )

    apply_custom_styles()

    # Initialize session state BEFORE accessing chatbot
    initialize_session_state()
    chatbot = st.session_state.chatbot

    # Application header
    st.markdown(
        f"""
        <div class="workspace-header">
            <div class="workspace-eyebrow">Your private knowledge workspace</div>
            <h1>{config.PAGE_TITLE}</h1>
            <p class="workspace-subtitle">{config.WELCOME_MESSAGE}</p>
            <div class="workspace-status">
                {"● Personal Assistant ready"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    # Sidebar
    with st.sidebar:
        st.header("📚 Upload Your Document")
        st.caption("Add PDFs to give your assistant context.")

        uploaded_files = st.file_uploader(
            "Upload PDF documents",
            type=["pdf"],
            accept_multiple_files=True,
        )

        if uploaded_files:
            valid_files = []

            for file in uploaded_files:
                if utils.validate_pdf_file(file):
                    valid_files.append(file)
                    st.success(
                        f"✅ {file.name} "
                        f"({utils.get_file_size_mb(file):.2f} MB)"
                    )
                else:
                    st.error(f"❌ {file.name} is not a valid PDF")

            if valid_files and st.button(
                "Process PDFs",
                type="primary",
            ):
                with st.spinner(config.PROCESSING_MESSAGE):
                    try:
                        success = chatbot.process_pdfs(valid_files)

                        if success:
                            st.success(config.SUCCESS_MESSAGE)
                            st.balloons()
                        else:
                            processing_error = getattr(
                                chatbot, "last_processing_error", None
                            )
                            if not processing_error:
                                processing_error = (
                                    "Restart the Streamlit app to load the "
                                    "updated PDF processing diagnostics, "
                                    "then try again."
                                )
                            st.error(
                                "Failed to process PDFs: "
                                f"{processing_error}"
                            )

                    except Exception as e:
                        st.error(config.ERROR_MESSAGE.format(str(e)))
                        logger.exception("Error processing PDFs")

        st.divider()
        st.header("⚙️ Workspace")

        if st.button("Clear Chat History"):
            chatbot.clear_chat_history()
            st.session_state[config.SESSION_MESSAGES] = []
            st.success("Chat history cleared!")

        if st.button(
            "Reset Chatbot",
            help="Clear all data and start fresh",
        ):
            chatbot.reset()
            st.session_state[config.SESSION_MESSAGES] = []
            st.success("Chatbot reset successfully!")
            st.rerun()

        st.divider()

        if chatbot.is_ready:
            st.success("Assistant is ready")
        else:
            st.info(config.UPLOAD_PROMPT)

        # Model information
        st.divider()

        with st.expander("Model Information"):
            model_info = getattr(
                chatbot.llm_handler,
                "model_info",
                {},
            )

            st.write(
                f"**Provider:** "
                f"{model_info.get('provider', 'Unknown')}"
            )
            st.write(
                f"**Model:** "
                f"{model_info.get('model', 'Unknown')}"
            )

            endpoint = model_info.get("endpoint")
            if endpoint:
                st.write(f"**Endpoint:** {endpoint}")

            st.write(
                f"**Temperature:** {config.LLM_TEMPERATURE}"
            )

    
    # Main chatbot/workspace: PDF is optional
    chat_tab, tasks_tab, notes_tab = st.tabs(
        ["💬 Chat Assistant", "✅ Tasks Reminder", "📝 Notes"]
    )

    with chat_tab:
        render_chat_tab(chatbot)

    with tasks_tab:
        with st.container(border=True):
            render_tasks_tab()

    with notes_tab:
        with st.container(border=True):
            render_notes_tab()


    # Developer credit - bottom right corner
    st.markdown(
        """
        <div class="developer-credit">
            Developed By: <span>Nadia Nova</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    
if __name__ == "__main__":
    main()
