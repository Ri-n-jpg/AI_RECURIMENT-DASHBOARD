# AI_RECURIMENT-DASHBOARD
The AI Recruitment Automation System is a web-based application built using Django and Groq AI that automates the candidate screening and hiring process. It helps recruiters efficiently manage resumes, evaluate candidates using AI-based scoring, and rank applicants based on skill relevance.  
🚀 AI Recruitment Dashboard

An AI-powered Recruitment Automation System that helps in candidate resume parsing, job matching, and smart screening using modern AI tools and backend automation.

📌 Features
📄 Resume Upload & Parsing (PDF support)
🤖 AI-based Candidate Evaluation (Groq AI / LLM integration)
🔍 Smart Job-Candidate Matching
📊 Recruitment Dashboard (Analytics-ready)
📬 Automated Candidate Processing Workflow
⚙️ REST API backend for integration
🧠 Supports future LinkedIn/job automation pipelines
🛠️ Tech Stack
Backend: Django / Django REST Framework
AI Integration: Groq API / LLM-based processing
Database: SQLite / PostgreSQL (configurable)
File Handling: PDF parsing (PyPDF / similar libraries)
Automation: Python scripts / API workflows
📁 Project Structure
AIAutomation/
│
├── job_automation/
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│
├── media/              # Uploaded resumes
├── requirements.txt
├── manage.py
└── README.md
⚙️ Installation & Setup
1. Clone the repository
git clone https://github.com/your-username/AI_RECURIMENT-DASHBOARD.git
cd AI_RECURIMENT-DASHBOARD
2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
3. Install dependencies
pip install -r requirements.txt
4. Run migrations
python manage.py migrate
5. Start server
python manage.py runserver
🔑 Environment Variables

Create a .env file:

GROQ_API_KEY=your_api_key_here
SECRET_KEY=your_django_secret_key
DEBUG=True
📊 How It Works
Recruiter uploads candidate resume (PDF)
System extracts text from resume
AI model analyzes skills, experience, and relevance
Candidate is scored and categorized
Data is stored in dashboard for filtering & review
🚀 Future Improvements
LinkedIn job scraping automation
Email automation for candidates
Advanced ranking system using embeddings
Power BI dashboard integration
Multi-role authentication system
👨‍💻 Author

Ritika Sharma

📄 License

This project is for educational and internship purposes.
