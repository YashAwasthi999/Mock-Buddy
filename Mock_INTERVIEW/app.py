from html import escape
import os
import sqlite3
import tempfile
import uuid
import streamlit as st

from AGENTS.interview_agent import InterviewAgent
from AGENTS.round_manager import AVAILBLE_ROUNDS
from CORE.audio_io import render_voice_player, speak_in_browser
from CORE.feedback_generator import generate_feedback_and_scores
from CORE.resume_parse import parse_resume
from CORE.storage import (
    DATA_UPLOAD_DIR,
    create_interview,
    get_interview,
    initialize_storage,
    list_interviews,
    save_answer,
    save_feedback,
)
from UTILS import config

st.set_page_config(page_title="MOCK BUDDY", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --buddy-ink: #eff4ff;
        --buddy-muted: #a4b1cc;
        --buddy-blue: #8a9dff;
        --buddy-teal: #5ce1d0;
        --buddy-line: rgba(196, 211, 255, .15);
        --buddy-paper: rgba(255, 255, 255, .065);
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(ellipse at 12% 0%, rgba(91, 111, 255, .24), transparent 34rem),
            radial-gradient(ellipse at 90% 20%, rgba(33, 195, 181, .12), transparent 32rem),
            #080d19;
        color: var(--buddy-ink);
    }
    [data-testid="stHeader"] { background: rgba(8, 13, 25, .55); }
    [data-testid="stMainBlockContainer"] {
        max-width: 1120px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }
    [data-testid="stSidebar"] {
        background: rgba(12, 19, 35, .82);
        border-right: 1px solid var(--buddy-line);
        backdrop-filter: blur(22px);
    }
    h1, h2, h3, p, label, [data-testid="stMarkdownContainer"] {
        color: var(--buddy-ink);
        letter-spacing: -.015em;
    }
    h1 { font-weight: 750; }
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stCaptionContainer"] {
        color: var(--buddy-muted);
    }
    [data-testid="stAlert"] {
        background: rgba(255, 255, 255, .07);
        border: 1px solid var(--buddy-line);
        border-radius: 14px;
        color: var(--buddy-ink);
        backdrop-filter: blur(18px);
    }
    [data-testid="stFileUploader"] section,
    [data-testid="stTextArea"] textarea,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        border-radius: 14px;
        border-color: var(--buddy-line);
        background: rgba(255, 255, 255, .055);
        color: var(--buddy-ink);
    }
    [data-testid="stTextArea"] textarea::placeholder { color: #8795b1; }
    [data-testid="stFileUploader"] section { background: rgba(255, 255, 255, .035); }
    [data-testid="stButton"] button {
        min-height: 2.75rem;
        border-radius: 11px;
        border: 1px solid var(--buddy-line);
        background: rgba(255, 255, 255, .075);
        color: var(--buddy-ink);
        font-weight: 650;
        transition: transform .15s ease, box-shadow .15s ease;
    }
    [data-testid="stButton"] button:hover {
        border-color: var(--buddy-blue);
        background: rgba(138, 157, 255, .14);
        box-shadow: 0 5px 24px rgba(83, 105, 255, .2);
        transform: translateY(-1px);
    }
    [data-testid="stButton"] button[kind="primary"] {
        border-color: rgba(138, 157, 255, .5);
        background: linear-gradient(120deg, rgba(89, 111, 242, .92), rgba(77, 183, 196, .8));
        color: #fff;
    }
    [data-testid="stProgress"] > div > div > div > div {
        background: linear-gradient(90deg, #8191ff, #4ee0ce);
    }
    [data-testid="stMetric"] {
        padding: 1rem;
        background: var(--buddy-paper);
        border: 1px solid var(--buddy-line);
        border-radius: 14px;
        backdrop-filter: blur(20px);
        box-shadow: 0 12px 35px rgba(0, 0, 0, .12);
    }
    .buddy-hero {
        padding: 1.5rem 1.7rem;
        margin: .4rem 0 1rem;
        border: 1px solid rgba(195, 209, 255, .2);
        border-radius: 20px;
        background:
            linear-gradient(120deg, rgba(255, 255, 255, .10), rgba(133, 156, 255, .08)),
            rgba(18, 27, 48, .58);
        box-shadow: 0 20px 55px rgba(0, 0, 0, .2);
        backdrop-filter: blur(24px);
    }
    .buddy-eyebrow {
        margin: 0 0 .35rem;
        color: #a9b5ff;
        font-size: .75rem;
        font-weight: 750;
        letter-spacing: .12em;
        text-transform: uppercase;
    }
    .buddy-title {
        margin: 0;
        color: #f3f6ff;
        font-size: clamp(2rem, 5vw, 3.1rem);
        font-weight: 800;
        letter-spacing: -.055em;
    }
    .buddy-subtitle {
        margin: .45rem 0 0;
        color: var(--buddy-muted);
        font-size: 1.02rem;
    }
    .buddy-question {
        padding: 1.25rem 1.4rem;
        border: 1px solid rgba(160, 177, 255, .2);
        border-left: 4px solid var(--buddy-blue);
        border-radius: 0 14px 14px 0;
        background: linear-gradient(120deg, rgba(107, 129, 255, .13), rgba(69, 207, 195, .055));
        color: #f2f5ff;
        font-size: 1.15rem;
        font-weight: 600;
        line-height: 1.65;
        backdrop-filter: blur(18px);
        box-shadow: 0 12px 32px rgba(0, 0, 0, .14);
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--buddy-line);
        background: rgba(255, 255, 255, .045);
        border-radius: 16px;
        backdrop-filter: blur(18px);
    }
    [data-testid="stExpander"] {
        border-color: var(--buddy-line);
        background: rgba(255, 255, 255, .035);
        border-radius: 14px;
    }
    [data-testid="stMarkdownContainer"] a { color: #a9b5ff; }
    </style>
    """,
    unsafe_allow_html=True,
)

UPLOAD_DIR = str(DATA_UPLOAD_DIR)

try:
    initialize_storage()
except (OSError, sqlite3.Error) as exc:
    st.error(f"Could not initialize local interview storage: {exc}")
    st.stop()


def save_uploaded_file(uploaded_file):
    """Save uploaded file temporarily for parsing."""
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        extension = os.path.splitext(os.path.basename(uploaded_file.name))[1].lower()
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix="resume_",
            suffix=extension,
            dir=UPLOAD_DIR,
            delete=False,
        ) as file:
            file.write(uploaded_file.getbuffer())
            return file.name
    except OSError as exc:
        st.error(f"Error saving uploaded file: {exc}")
        return None


def cleanup_temp_files(file_path):
    """Remove a specific temporary file."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as exc:
        st.warning(f"Could not remove temporary file {file_path}: {exc}")


if "stage" not in st.session_state:
    st.session_state.stage = "upload"
if "resume_text" not in st.session_state:
    st.session_state.resume_text = None
if "interview_agent" not in st.session_state:
    st.session_state.interview_agent = None
if "selected_round_key" not in st.session_state:
    st.session_state.selected_round_key = None
if "questions" not in st.session_state:
    st.session_state.questions = []
if "current_question_index" not in st.session_state:
    st.session_state.current_question_index = 0
if "interview_history" not in st.session_state:
    st.session_state.interview_history = []
if "feedback" not in st.session_state:
    st.session_state.feedback = None
if "temp_resume_path" not in st.session_state:
    st.session_state.temp_resume_path = None
if "resume_filename" not in st.session_state:
    st.session_state.resume_filename = None
if "current_interview_id" not in st.session_state:
    st.session_state.current_interview_id = None
if "feedback_saved" not in st.session_state:
    st.session_state.feedback_saved = False
if "interview_owner_id" not in st.session_state:
    st.session_state.interview_owner_id = uuid.uuid4().hex

if config.QUESTION_DEMO_MODE or config.FEEDBACK_DEMO_MODE:
    missing_ai_features = []
    if config.QUESTION_DEMO_MODE:
        missing_ai_features.append("question generation may use demo content")
    if config.FEEDBACK_DEMO_MODE:
        missing_ai_features.append("AI-generated feedback and scores require a feedback API key")
    st.warning("AI configuration notice: " + "; ".join(missing_ai_features) + ".")

st.markdown(
    """
    <section class="buddy-hero">
      <p class="buddy-eyebrow">Your personal interview practice space</p>
      <h1 class="buddy-title">Mock Buddy</h1>
      <p class="buddy-subtitle">Build confidence, one thoughtful answer at a time.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

stage_labels = ["Resume", "Round", "Interview", "Feedback"]
stage_index = {
    "upload": 0,
    "select_round": 1,
    "interviewing": 2,
    "feedback": 3,
}.get(st.session_state.stage, 0)
st.progress((stage_index + 1) / len(stage_labels))
st.caption(f"Step {stage_index + 1} of {len(stage_labels)} · " + "  →  ".join(
    f"**{label}**" if index == stage_index else label
    for index, label in enumerate(stage_labels)
))

if st.session_state.stage == "upload":
    if not st.session_state.get("welcome_autoplay_attempted", False):
        render_voice_player(
            "Welcome to Mock Buddy. Upload your resume to begin, then type your answers during the interview.",
            "Play welcome",
            auto_play=True,
        )
        st.session_state.welcome_autoplay_attempted = True

st.sidebar.header("Your practice space")
st.sidebar.info(
    "Practice interview questions tailored to your resume, then get actionable feedback and "
    "a score for every answer."
)
st.sidebar.caption("A relaxed space to practice, reflect, and improve.")
render_voice_player(
    "Hello, I'm Mock Buddy. I'll help you practice and build confidence, one question at a time.",
    "Preview interviewer voice",
)
st.sidebar.caption(
    "Interview data and temporary recordings are stored in Mock_INTERVIEW/DATA/uploads."
)

with st.sidebar.expander("Saved interview history"):
    try:
        saved_interviews = list_interviews(
            owner_id=st.session_state.interview_owner_id
        )
    except (OSError, sqlite3.Error) as exc:
        st.error(f"Could not load saved interview history: {exc}")
        saved_interviews = []

    if saved_interviews:
        interview_by_id = {item["id"]: item for item in saved_interviews}
        selected_interview_id = st.selectbox(
            "Recent interviews",
            options=list(interview_by_id),
            format_func=lambda interview_id: (
                f"{interview_by_id[interview_id]['started_at'][:16].replace('T', ' ')} "
                f"- {interview_by_id[interview_id]['round_name']} "
                f"({interview_by_id[interview_id]['status']})"
            ),
            key="saved_interview_select",
        )
        try:
            saved_interview = get_interview(
                selected_interview_id,
                owner_id=st.session_state.interview_owner_id,
            )
        except (OSError, sqlite3.Error) as exc:
            st.error(f"Could not load the selected interview: {exc}")
            saved_interview = None

        if saved_interview:
            st.caption(f"Resume: {saved_interview['resume_filename']}")
            if saved_interview["status"] == "in_progress" and st.button(
                "Resume this interview",
                key=f"resume_interview_{selected_interview_id}",
            ):
                st.session_state.interview_agent = InterviewAgent(
                    saved_interview["resume_text"]
                )
                st.session_state.resume_text = saved_interview["resume_text"]
                st.session_state.resume_filename = saved_interview["resume_filename"]
                st.session_state.selected_round_key = saved_interview["round_key"]
                st.session_state.questions = [
                    answer["question"] for answer in saved_interview["answers"]
                ]
                st.session_state.interview_history = [
                    {"question": answer["question"], "answer": answer["answer"]}
                    for answer in saved_interview["answers"]
                    if answer["answer"]
                ]
                st.session_state.current_question_index = next(
                    (
                        index
                        for index, answer in enumerate(saved_interview["answers"])
                        if not answer["answer"]
                    ),
                    len(saved_interview["answers"]),
                )
                st.session_state.current_interview_id = selected_interview_id
                st.session_state.feedback = None
                st.session_state.feedback_saved = False
                st.session_state.stage = "interviewing"
                for key in list(st.session_state.keys()):
                    if key.startswith("spoken_q"):
                        del st.session_state[key]
                st.rerun()

            for index, answer in enumerate(saved_interview["answers"], start=1):
                st.markdown(f"**Q{index}:** {answer['question']}")
                st.markdown(f"**Your answer:** {answer['answer'] or 'Not answered'}")
                if answer["score"] is not None:
                    st.markdown(f"**Score:** {answer['score']}/10")
            if saved_interview["overall_feedback"]:
                st.markdown("**Overall feedback**")
                st.write(saved_interview["overall_feedback"])
                st.markdown("**Suggestions**")
                st.write(saved_interview["suggestions"])
                st.markdown(
                    f"**Total score:** {saved_interview['total_score']}/"
                    f"{saved_interview['max_score']}"
                )
    else:
        st.caption("Completed and in-progress interview data is saved on this device.")

uploaded_file = None
if st.session_state.stage == "upload":
    st.header("Start with your resume")
    st.markdown(
        "Your resume helps the interviewer ask questions that connect to **your projects, "
        "skills, and experience**. Your interview history is saved locally on this device."
    )
    uploaded_file = st.file_uploader("Choose a resume file (PDF or DOCX)", type=["pdf", "docx"])
    st.caption("Supported formats: PDF and DOCX · Tip: use a text-based PDF for the best parsing results.")

    if uploaded_file is not None:
        st.session_state.temp_resume_path = save_uploaded_file(uploaded_file)
        if st.session_state.temp_resume_path:
            st.session_state.resume_filename = uploaded_file.name
            with st.spinner("Parsing resume..."):
                try:
                    st.session_state.resume_text = parse_resume(
                        st.session_state.temp_resume_path
                    )
                finally:
                    cleanup_temp_files(st.session_state.temp_resume_path)
                    st.session_state.temp_resume_path = None

            if st.session_state.resume_text:
                st.success("Resume parsed successfully.")
                try:
                    st.session_state.interview_agent = InterviewAgent(st.session_state.resume_text)
                    st.session_state.stage = "select_round"
                    st.rerun()
                except Exception as exc:
                    st.error(f"Failed to initialize interview agent: {exc}")
                    st.session_state.resume_text = None
                    st.session_state.interview_agent = None
                    cleanup_temp_files(st.session_state.temp_resume_path)
                    st.session_state.temp_resume_path = None
            else:
                st.error("Could not extract text from the resume. Please try a different file.")
                cleanup_temp_files(st.session_state.temp_resume_path)
                st.session_state.temp_resume_path = None

if st.session_state.stage == "select_round":
    st.header("Choose your practice round")
    st.markdown("Pick the kind of conversation you want to practice. There’s no pressure—this is a space to learn.")

    if not st.session_state.interview_agent:
        st.error("Interview agent not initialized. Please upload a resume first.")
        st.session_state.stage = "upload"
        cleanup_temp_files(st.session_state.temp_resume_path)
        st.session_state.temp_resume_path = None
        st.rerun()

    round_options = {key: info["name"] for key, info in AVAILBLE_ROUNDS.items()}
    st.session_state.selected_round_key = st.selectbox(
        "Choose the type of interview round:",
        options=list(round_options.keys()),
        format_func=lambda key: round_options[key],
        key="round_select",
    )
    selected_round = AVAILBLE_ROUNDS[st.session_state.selected_round_key]
    st.info(
        f"**{selected_round['name']} round** · {selected_round['num_questions']} questions · "
        "Take your time and answer in your own words."
    )
    with st.expander("A quick tip before you begin"):
        st.markdown(
            "For experience-based questions, try **STAR**: describe the Situation, your Task, "
            "the Actions you took, and the Result. Specific examples make strong answers."
        )

    if st.button("Start my interview  →", key="start_interview_btn", type="primary"):
        if st.session_state.selected_round_key:
            for key in list(st.session_state.keys()):
                if key.startswith("spoken_q"):
                    del st.session_state[key]

            round_info = AVAILBLE_ROUNDS[st.session_state.selected_round_key]
            agent = st.session_state.interview_agent
            if agent:
                with st.spinner(f"Generating questions for the {round_info['name']} round..."):
                    st.session_state.questions = agent.generate_questions_for_round(
                        round_info["name"],
                        round_info["num_questions"],
                    )
                    st.session_state.current_question_index = 0
                    st.session_state.interview_history = []
                    st.session_state.feedback = None
                    st.session_state.current_interview_id = None
                    st.session_state.feedback_saved = False

                    if st.session_state.questions:
                        try:
                            st.session_state.current_interview_id = create_interview(
                                resume_filename=st.session_state.resume_filename or "resume",
                                resume_text=st.session_state.resume_text,
                                round_key=st.session_state.selected_round_key,
                                round_name=round_info["name"],
                                questions=st.session_state.questions,
                                owner_id=st.session_state.interview_owner_id,
                            )
                        except (OSError, sqlite3.Error, ValueError) as exc:
                            st.error(f"Could not save this interview before starting: {exc}")
                            st.session_state.questions = []
                            st.stop()

                    try:
                        speak_in_browser(
                            f"Welcome to the {round_info['name']} round. I will ask you {len(st.session_state.questions)} questions. Let's begin with the first question."
                        )
                    except Exception as exc:
                        st.warning(f"Could not play welcome audio: {exc}. Starting interview.")

                st.session_state.stage = "interviewing"
                st.rerun()
            else:
                st.error("Failed to generate questions for the round. Please try selecting again or check your API keys.")
        else:
            st.error("Please choose a round before starting.")

if st.session_state.stage == "interviewing":
    round_name = AVAILBLE_ROUNDS[st.session_state.selected_round_key]["name"]
    st.header(f"Your {round_name} practice interview")

    if not st.session_state.questions:
        st.error("No questions loaded for this round. Please select the round again.")
        if st.button("Go back to round selection"):
            st.session_state.stage = "select_round"
            st.rerun()
        st.stop()

    q_index = st.session_state.current_question_index
    if q_index < len(st.session_state.questions):
        current_question = st.session_state.questions[q_index]
        st.progress(q_index / len(st.session_state.questions))
        st.caption(f"QUESTION {q_index + 1} OF {len(st.session_state.questions)}")
        st.markdown(
            f'<div class="buddy-question">{escape(current_question)}</div>',
            unsafe_allow_html=True,
        )
        st.caption("Take a breath, think of a real example, and answer as if you were talking to a person.")

        render_voice_player(
            current_question,
            "🔊 Listen to question",
            auto_play=f"spoken_q{q_index}" not in st.session_state,
        )
        st.session_state[f"spoken_q{q_index}"] = True

        st.markdown("#### Your answer")
        answer_key = f"answer_q{q_index}"
        answer_value = st.text_area(
            "Write your answer in your own words",
            key=answer_key,
            height=180,
            placeholder="A useful answer includes the situation, what you did, and what changed...",
            label_visibility="collapsed",
        )
        word_count = len(answer_value.strip().split()) if answer_value else 0
        st.caption(f"{word_count} words · A few clear sentences are a great start.")

        if st.button("Send answer  →", key=f"submit_q{q_index}", type="primary"):
            if answer_value and answer_value.strip():
                try:
                    save_answer(
                        st.session_state.current_interview_id,
                        q_index,
                        answer_value,
                        owner_id=st.session_state.interview_owner_id,
                    )
                except (OSError, sqlite3.Error, ValueError) as exc:
                    st.error(f"Could not save your answer. It has not been submitted: {exc}")
                    st.stop()

                st.session_state.interview_history.append(
                    {"question": current_question, "answer": answer_value.strip()}
                )

                st.session_state.current_question_index += 1
                if st.session_state.current_question_index >= len(st.session_state.questions):
                    st.session_state.stage = "feedback"
                    try:
                        speak_in_browser("Thank you for sharing your answers. You did it. I will now prepare your personalized feedback.")
                    except Exception as exc:
                        st.warning(f"Audio notification error: {exc}")
                    st.rerun()
                else:
                    try:
                        speak_in_browser("Thanks for sharing that. Let's move on to the next question.")
                    except Exception as exc:
                        st.warning(f"Audio notification error: {exc}")
                    st.rerun()
            else:
                st.warning("Please enter your answer before submitting.")
    else:
        st.session_state.stage = "feedback"
        st.rerun()

if st.session_state.stage == "feedback":
    st.header("You did it — here’s your interview reflection")
    st.markdown(
        "Every practice round is progress. Here’s personalized feedback to help you feel "
        "more prepared for the next conversation."
    )

    round_name = AVAILBLE_ROUNDS[st.session_state.selected_round_key]["name"]
    agent = st.session_state.interview_agent

    feedback_error = False
    if not st.session_state.feedback and agent and st.session_state.interview_history:
        with st.spinner("Generating feedback... This may take a few moments."):
            try:
                st.session_state.feedback = generate_feedback_and_scores(
                    resume_text=st.session_state.resume_text,
                    round_name=round_name,
                    qa_pairs=st.session_state.interview_history,
                )
            except Exception as exc:
                feedback_error = True
                st.error(f"Failed to generate AI feedback and scores: {exc}")

    if st.session_state.feedback and not st.session_state.feedback_saved:
        try:
            save_feedback(
                st.session_state.current_interview_id,
                st.session_state.feedback,
                owner_id=st.session_state.interview_owner_id,
            )
            st.session_state.feedback_saved = True
            st.success("Your answers, resume, feedback, and scores are saved locally.")
        except (OSError, sqlite3.Error, KeyError, TypeError, ValueError) as exc:
            st.error(f"Feedback is available below, but could not be saved to history: {exc}")

    if st.session_state.feedback:
        feedback_data = st.session_state.feedback

        scores = feedback_data.get("scores_per_question", [])
        total_score = feedback_data.get("total_score", 0)
        max_score = len(st.session_state.interview_history) * 10

        if scores and len(scores) == len(st.session_state.interview_history):
            score_columns = st.columns(len(scores))
            for index, (column, score) in enumerate(zip(score_columns, scores)):
                with column:
                    st.metric(f"Question {index + 1}", f"{score}/10")
                    st.progress(score / 10)
        elif scores:
            st.warning(
                f"Note: Number of scores ({len(scores)}) doesn't match number of questions ({len(st.session_state.interview_history)}). Displaying raw scores: {scores}"
            )
        else: 
            st.markdown("Scores could not be determined.")

        if max_score > 0:
            st.metric("Round score", f"{total_score}/{max_score}")
        else:
            st.markdown("N/A (No questions answered)")

        feedback_column, suggestions_column = st.columns(2)
        with feedback_column:
            with st.container(border=True):
                st.subheader("What went well")
                st.markdown(feedback_data.get("overall_feedback", "N/A"))
        with suggestions_column:
            with st.container(border=True):
                st.subheader("Ideas for your next answer")
                st.markdown(feedback_data.get("suggestions", "N/A"))
    elif not feedback_error:
        st.warning("Feedback is not available for this round.")

    st.markdown("---")
    if st.button("Start Another Round"):
        st.session_state.stage = "select_round"
        st.session_state.selected_round_key = None
        st.session_state.questions = []
        st.session_state.current_question_index = 0
        st.session_state.interview_history = []
        st.session_state.feedback = None
        st.session_state.current_interview_id = None
        st.session_state.feedback_saved = False
        for key in list(st.session_state.keys()):
            if key.startswith("spoken_q") or key.startswith("answer_q") or key.startswith("submit_q"):
                del st.session_state[key]
        st.rerun()
        

    if st.button("Upload a New Resume"):
        cleanup_temp_files(st.session_state.temp_resume_path)
        for key in list(st.session_state.keys()):
            if key != "interview_owner_id":
                del st.session_state[key]
        st.session_state.stage = "upload"
        st.rerun()




  