# # streamlit_app.py
# """
# KCET Math Solver Chatbot - Streamlit Frontend
# Interactive chatbot interface for the KCET Math Solver pipeline
# """

# import streamlit as st
# import tempfile
# import json
# import pandas as pd
# from pathlib import Path
# import sys
# import time
# from typing import Dict, Any, Optional

# # Add project root to path
# ROOT = Path(__file__).parent.resolve()
# if str(ROOT) not in sys.path:
#     sys.path.append(str(ROOT))

# try:
#     from src.main import KCETMathSolver, setup_notebook_environment
#     from src.utils.io import load_answer_key_flexible
# except ImportError as e:
#     st.error(f"Import error: {e}")
#     st.error("Make sure to run from project root directory with: streamlit run streamlit_app.py")
#     st.stop()


# class KCETChatbot:
#     """Chatbot wrapper for KCET Math Solver"""
    
#     def __init__(self):
#         self.solver = None
#         self.session_data = {}
    
#     def initialize_solver(self, file_path: str) -> Dict[str, Any]:
#         """Initialize solver with uploaded file"""
#         try:
#             self.solver = KCETMathSolver()
#             result = self.solver.run_p1_ingestion(file_path, use_enhanced_parser=True)
            
#             if result["status"] == "success":
#                 self.session_data = {
#                     "file_path": file_path,
#                     "questions_parsed": len(self.solver.qtexts),
#                     "questions_with_figures": sum(self.solver.figures.values()),
#                     "parsing_stats": result["stats"]
#                 }
            
#             return result
#         except Exception as e:
#             return {"status": "error", "error": str(e)}
    
#     def process_chat_query(self, query: str) -> str:
#         """Process user chat query and return response"""
#         if not self.solver:
#             return "Please upload a KCET paper first to get started."
        
#         query_lower = query.lower().strip()
        
#         # Handle different types of queries
#         if any(phrase in query_lower for phrase in ["hello", "hi", "hey"]):
#             return self._handle_greeting()
        
#         elif any(phrase in query_lower for phrase in ["help", "what can you do"]):
#             return self._handle_help()
        
#         elif any(phrase in query_lower for phrase in ["how many questions", "question count"]):
#             return self._handle_question_count()
        
#         elif "show question" in query_lower:
#             return self._handle_show_question(query)
        
#         elif any(phrase in query_lower for phrase in ["solve all", "solve questions", "run solver"]):
#             return self._handle_solve_all()
        
#         elif any(phrase in query_lower for phrase in ["parse", "parsing", "ingestion"]):
#             return self._handle_parsing_info()
        
#         elif any(phrase in query_lower for phrase in ["accuracy", "evaluation", "results"]):
#             return self._handle_results()
        
#         elif any(phrase in query_lower for phrase in ["algebra", "calculus", "geometry", "topic"]):
#             return self._handle_topic_query(query)
        
#         elif "status" in query_lower:
#             return self._handle_status()
        
#         else:
#             return self._handle_unknown_query(query)
    
#     def _handle_greeting(self) -> str:
#         return (
#             "Hello! I'm your KCET Math Solver assistant. "
#             f"I can help you with {self.session_data.get('questions_parsed', 0)} questions "
#             "from your uploaded paper. Ask me to solve questions, show specific questions, "
#             "or get information about the paper!"
#         )
    
#     def _handle_help(self) -> str:
#         return """
# I can help you with:

# 📋 **Document Analysis**
# - "How many questions are there?"
# - "Show me question 5"
# - "What's the parsing status?"

# 🔧 **Solving**  
# - "Solve all questions"
# - "Run the solver"
# - "Get results"

# 📊 **Analysis**
# - "Show accuracy"
# - "Find algebra questions"
# - "Show statistics"

# 💡 **Examples**
# - "Show me question 10"
# - "Solve questions 1 to 20"
# - "What topics are covered?"
# """
    
#     def _handle_question_count(self) -> str:
#         count = self.session_data.get('questions_parsed', 0)
#         with_figures = self.session_data.get('questions_with_figures', 0)
        
#         response = f"I found **{count} questions** in your paper."
#         if with_figures > 0:
#             response += f" {with_figures} of them contain figures or diagrams."
        
#         return response
    
#     def _handle_show_question(self, query: str) -> str:
#         # Extract question number
#         import re
#         numbers = re.findall(r'\d+', query)
        
#         if not numbers:
#             return "Please specify a question number, like 'show question 5'"
        
#         q_num = int(numbers[0])
#         q_key = f"q{q_num}"
        
#         if q_key not in self.solver.qtexts:
#             return f"Question {q_num} not found. Available questions: 1 to {len(self.solver.qtexts)}"
        
#         question_text = self.solver.qtexts[q_key]
#         options = self.solver.options.get(q_key, [])
#         has_figure = self.solver.figures.get(q_key, False)
        
#         response = f"**Question {q_num}:**\n\n{question_text}\n\n"
        
#         if options:
#             response += "**Options:**\n"
#             for i, option in enumerate(options, 1):
#                 response += f"{i}. {option}\n"
        
#         if has_figure:
#             response += "\n📷 *This question contains a figure/diagram*"
        
#         # Show answer if available
#         if hasattr(self.solver, 'answers') and f"q{q_num}" in self.solver.answers:
#             answer_data = self.solver.answers[f"q{q_num}"]
#             if isinstance(answer_data, dict) and "option" in answer_data:
#                 response += f"\n\n**My Answer:** Option {answer_data['option']}"
#                 if "explain" in answer_data:
#                     response += f"\n**Explanation:** {answer_data['explain']}"
        
#         return response
    
#     def _handle_solve_all(self) -> str:
#         try:
#             with st.spinner("Running solver pipeline..."):
#                 result = self.solver.run_p2_to_p7_pipeline(batch_size=20, verbose=True)
            
#             if result["status"] == "success":
#                 answered = result.get("total_answered", 0)
#                 return f"✅ Successfully solved {answered} questions! The results have been saved. Ask me about 'results' or 'accuracy' to see how I did."
#             else:
#                 return f"❌ Solving failed: {result.get('error', 'Unknown error')}"
                
#         except Exception as e:
#             return f"❌ Error during solving: {str(e)}"
    
#     def _handle_parsing_info(self) -> str:
#         stats = self.session_data.get('parsing_stats', {})
        
#         response = "**Parsing Information:**\n\n"
#         response += f"- Total questions: {stats.get('total_questions', 'N/A')}\n"
#         response += f"- Questions with 4 options: {stats.get('questions_with_4_options', 'N/A')}\n"
#         response += f"- Questions with figures: {stats.get('questions_with_figures', 'N/A')}\n"
#         response += f"- Parsing method: {stats.get('parsing_method', 'N/A')}\n"
#         response += f"- Source file: {stats.get('source_file', 'N/A')}"
        
#         return response
    
#     def _handle_results(self) -> str:
#         if not hasattr(self.solver, 'answers') or not self.solver.answers:
#             return "No results yet! Ask me to 'solve all questions' first."
        
#         total_answered = len(self.solver.answers)
#         total_questions = len(self.solver.qtexts)
        
#         response = f"**Results Summary:**\n\n"
#         response += f"- Questions answered: {total_answered}/{total_questions}\n"
        
#         if self.solver.predictions_path:
#             # Try to get accuracy if answer key is available
#             try:
#                 df = pd.read_csv(self.solver.predictions_path)
#                 if "qtype" in df.columns:
#                     type_counts = df["qtype"].value_counts()
#                     response += f"\n**By Topic:**\n"
#                     for topic, count in type_counts.items():
#                         response += f"- {topic}: {count} questions\n"
#             except Exception:
#                 pass
        
#         return response
    
#     def _handle_topic_query(self, query: str) -> str:
#         if not hasattr(self.solver, 'qtexts'):
#             return "Please solve questions first to get topic information."
        
#         # This is a simplified topic search - in practice, you'd use the router
#         from src.utils.normalize import detect_question_topics
        
#         topic_matches = []
#         query_lower = query.lower()
        
#         for q_key, q_text in self.solver.qtexts.items():
#             topics = detect_question_topics(q_text)
#             q_num = q_key[1:]  # Remove 'q' prefix
            
#             if any(topic in query_lower for topic in topics):
#                 topic_matches.append((q_num, topics[0] if topics else "unknown"))
        
#         if topic_matches:
#             response = f"Found {len(topic_matches)} questions matching your topic:\n\n"
#             for q_num, topic in topic_matches[:10]:  # Show first 10
#                 response += f"- Question {q_num} ({topic})\n"
            
#             if len(topic_matches) > 10:
#                 response += f"\n... and {len(topic_matches) - 10} more"
#         else:
#             response = "No questions found matching that topic. Try: algebra, calculus, geometry, trigonometry, statistics, discrete"
        
#         return response
    
#     def _handle_status(self) -> str:
#         status_info = []
        
#         if self.solver:
#             status_info.append("✅ Solver initialized")
#             status_info.append(f"✅ {len(self.solver.qtexts)} questions parsed")
            
#             if hasattr(self.solver, 'answers') and self.solver.answers:
#                 status_info.append(f"✅ {len(self.solver.answers)} questions solved")
#             else:
#                 status_info.append("⏳ Questions not solved yet")
            
#             if self.solver.predictions_path:
#                 status_info.append(f"✅ Results saved to: {Path(self.solver.predictions_path).name}")
            
#         return "**System Status:**\n\n" + "\n".join(status_info)
    
#     def _handle_unknown_query(self, query: str) -> str:
#         return (
#             f"I'm not sure how to help with '{query}'. "
#             "Try asking me to:\n"
#             "- Show a specific question\n"
#             "- Solve all questions\n"
#             "- Show results or accuracy\n"
#             "- Get help for more options"
#         )


# # Streamlit App Configuration
# st.set_page_config(
#     page_title="KCET Math Solver",
#     page_icon="🧮",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Initialize session state
# if "chatbot" not in st.session_state:
#     st.session_state.chatbot = KCETChatbot()

# if "messages" not in st.session_state:
#     st.session_state.messages = []

# if "file_uploaded" not in st.session_state:
#     st.session_state.file_uploaded = False


# def main():
#     """Main Streamlit app"""
    
#     # Header
#     st.title("🧮 KCET Math Solver Chatbot")
#     st.markdown("*Upload a KCET paper and chat with me to solve math problems!*")
    
#     # Sidebar
#     with st.sidebar:
#         st.header("📁 Upload Paper")
        
#         # File upload
#         uploaded_file = st.file_uploader(
#             "Choose a KCET paper file",
#             type=['txt', 'pdf'],
#             help="Upload a TXT or PDF file containing KCET math questions"
#         )
        
#         if uploaded_file and not st.session_state.file_uploaded:
#             with st.spinner("Processing your paper..."):
#                 # Save uploaded file temporarily
#                 with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{uploaded_file.name.split(".")[-1]}') as tmp:
#                     tmp.write(uploaded_file.getvalue())
#                     temp_path = tmp.name
                
#                 # Initialize chatbot with file
#                 result = st.session_state.chatbot.initialize_solver(temp_path)
                
#                 if result["status"] == "success":
#                     st.session_state.file_uploaded = True
#                     st.success("✅ Paper processed successfully!")
                    
#                     stats = result["stats"]
#                     st.metric("Questions Found", stats["total_questions"])
#                     st.metric("With Figures", stats["questions_with_figures"])
                    
#                     # Add welcome message
#                     welcome_msg = st.session_state.chatbot.process_chat_query("hello")
#                     st.session_state.messages.append({
#                         "role": "assistant",
#                         "content": welcome_msg
#                     })
                    
#                 else:
#                     st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
        
#         # Show current session info
#         if st.session_state.file_uploaded:
#             st.header("📊 Session Info")
#             chatbot = st.session_state.chatbot
            
#             col1, col2 = st.columns(2)
#             with col1:
#                 st.metric("Questions", chatbot.session_data.get('questions_parsed', 0))
#             with col2:
#                 st.metric("With Figures", chatbot.session_data.get('questions_with_figures', 0))
            
#             # Quick actions
#             st.header("⚡ Quick Actions")
#             if st.button("🔧 Solve All Questions", use_container_width=True):
#                 response = chatbot.process_chat_query("solve all questions")
#                 st.session_state.messages.append({
#                     "role": "assistant", 
#                     "content": response
#                 })
#                 st.rerun()
            
#             if st.button("📋 Show Status", use_container_width=True):
#                 response = chatbot.process_chat_query("status")
#                 st.session_state.messages.append({
#                     "role": "assistant",
#                     "content": response
#                 })
#                 st.rerun()
    
#     # Main chat interface
#     if st.session_state.file_uploaded:
#         # Display chat messages
#         for message in st.session_state.messages:
#             with st.chat_message(message["role"]):
#                 st.markdown(message["content"])
        
#         # Chat input
#         if prompt := st.chat_input("Ask me about the questions or tell me what to do..."):
#             # Add user message
#             st.session_state.messages.append({"role": "user", "content": prompt})
#             with st.chat_message("user"):
#                 st.markdown(prompt)
            
#             # Generate response
#             with st.chat_message("assistant"):
#                 with st.spinner("Thinking..."):
#                     response = st.session_state.chatbot.process_chat_query(prompt)
                
#                 st.markdown(response)
#                 st.session_state.messages.append({
#                     "role": "assistant",
#                     "content": response
#                 })
    
#     else:
#         # Instructions when no file uploaded
#         st.info("👆 Please upload a KCET paper file to get started!")
        
#         with st.expander("ℹ️ How to use this chatbot"):
#             st.markdown("""
#             1. **Upload** a KCET paper (TXT or PDF) using the sidebar
#             2. **Chat** with me to explore and solve questions
#             3. **Ask** me to show specific questions, solve all questions, or get results
            
#             **Example questions:**
#             - "How many questions are there?"
#             - "Show me question 5"
#             - "Solve all questions"
#             - "What's my accuracy?"
#             - "Find algebra questions"
#             """)
    
#     # Footer
#     st.markdown("---")
#     st.markdown("*Built with Streamlit and the KCET Math Solver Pipeline*")


# if __name__ == "__main__":
#     main()


# # Additional utility functions for Streamlit

# def create_download_button(results: Dict[str, Any]) -> None:
#     """Create download buttons for results"""
#     if "predictions_path" in results:
#         try:
#             df = pd.read_csv(results["predictions_path"])
#             csv = df.to_csv(index=False)
#             st.download_button(
#                 label="📥 Download Results (CSV)",
#                 data=csv,
#                 file_name="kcet_results.csv",
#                 mime="text/csv"
#             )
#         except Exception:
#             pass


# def show_question_browser(chatbot: KCETChatbot) -> None:
#     """Create an interactive question browser"""
#     if not chatbot.solver or not chatbot.solver.qtexts:
#         return
    
#     st.subheader("🔍 Question Browser")
    
#     questions = list(chatbot.solver.qtexts.keys())
#     selected_q = st.selectbox("Select a question:", questions, format_func=lambda x: f"Question {x[1:]}")
    
#     if selected_q:
#         response = chatbot.process_chat_query(f"show question {selected_q[1:]}")
#         st.markdown(response)


# def create_results_dashboard(chatbot: KCETChatbot) -> None:
#     """Create a results dashboard"""
#     if not chatbot.solver or not hasattr(chatbot.solver, 'answers'):
#         return
    
#     st.subheader("📊 Results Dashboard")
    
#     # Basic metrics
#     col1, col2, col3 = st.columns(3)
    
#     with col1:
#         st.metric("Total Questions", len(chatbot.solver.qtexts))
    
#     with col2:
#         answered = len(chatbot.solver.answers) if chatbot.solver.answers else 0
#         st.metric("Answered", answered)
    
#     with col3:
#         if chatbot.solver.predictions_path:
#             st.metric("Results File", "Available")
#         else:
#             st.metric("Results File", "Not Ready")