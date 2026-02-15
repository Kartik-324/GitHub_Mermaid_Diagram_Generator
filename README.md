# 🚀 GitHub-Mermaid Diagram Generator

GitHub-Mermaid Diagram Generator is an AI-powered tool that converts any GitHub repository into **clear, interactive, and visually rich Mermaid diagrams**.  
It helps developers, students, and teams quickly understand complex codebases by visualizing architecture, workflows, database schemas, and system interactions.

Using advanced Large Language Models, the system deeply analyzes repositories and generates accurate diagrams that can be rendered, customized, and downloaded in real time.

![image alt](https://github.com/Kartik-324/RepoVision_AI/blob/7b9e5ddeff01be9146dfb973a9bd3571978ef5ee/Screenshot%202026-01-11%20115447.png)

![image alt](https://github.com/Kartik-324/RepoVision_AI/blob/7b9e5ddeff01be9146dfb973a9bd3571978ef5ee/Screenshot%202026-01-11%20115519.png)

![image alt](https://github.com/Kartik-324/RepoVision_AI/blob/7b9e5ddeff01be9146dfb973a9bd3571978ef5ee/Screenshot%202026-01-11%20115539.png)

![image alt](https://github.com/Kartik-324/RepoVision_AI/blob/7b9e5ddeff01be9146dfb973a9bd3571978ef5ee/Screenshot%202025-12-04%20144116.png)

![image alt](https://github.com/Kartik-324/RepoVision_AI/blob/7b9e5ddeff01be9146dfb973a9bd3571978ef5ee/Screenshot%202025-12-04%20144127.png)

![image alt](https://github.com/Kartik-324/RepoVision_AI/blob/7b9e5ddeff01be9146dfb973a9bd3571978ef5ee/Screenshot%202025-12-04%20144153.png)


---

## ✨ Features

### 🎨 Supported Diagram Types

- **Sequence Diagrams** – Visualize request flow and API interactions  
- **Component Diagrams** – High-level system architecture  
- **ER / Database Diagrams** – Tables, relations, and schemas  
- **Flowcharts** – Business logic and execution flow  
- **Class Diagrams** – OOP structure and inheritance  
- **State Diagrams** – State transitions and lifecycle  
- **User Journey Maps** – End-user flow visualization  
- **Gantt Charts** – Timeline and task dependencies  
- **Mindmaps** – High-level project overview  

---

## 💬 Intelligent Chat Interface

- Ask **natural language questions** about any GitHub repository  
- Generate diagrams instantly using chat prompts  
- Get **visual explanations** of complex architectures  
- Ideal for onboarding, documentation, and learning  

---

## 🎯 Smart Capabilities

- Deep GitHub repository scanning (files & structure)  
- Accurate diagram generation using **GPT-4o**  
- Real-time Mermaid rendering  
- Dark & Light theme support  
- Diagram history tracking  
- Download diagrams as images or Mermaid code  

---

## 📋 Prerequisites

Make sure you have the following installed:

- Python **3.8 or higher**
- OpenAI API Key
- GitHub Personal Access Token *(optional but recommended to avoid rate limits)*

---

## 🚀 Quick Start

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Kartik-324/RepoVision-AI.git
cd github-mermaid-generator

2️⃣ Backend Setup
bash
Copy code
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
Create a .env file inside the backend directory:

env
Copy code
OPENAI_API_KEY=your_openai_api_key
GITHUB_TOKEN=your_github_token

3️⃣ Frontend Setup
bash
Copy code
cd ../frontend
pip install -r requirements.txt

4️⃣ Run the Application
Backend Server
bash
Copy code
uvicorn main:app --reload --host 0.0.0.0 --port 8000
Frontend (Streamlit)
bash
Copy code
streamlit run app.py


🌐 Access URLs
Frontend UI: http://localhost:8501

Backend API: http://localhost:8000

Swagger Docs: http://localhost:8000/docs

📁 Project Structure
bash
Copy code
github-mermaid-generator/
│
├── backend/
│   ├── main.py            # FastAPI entry point
│   ├── models.py          # Pydantic models
│   ├── routes/            # API routes
│   ├── services/          # Repo analysis & diagram logic
│
├── frontend/
│   ├── app.py             # Streamlit main app
│   ├── components/        # UI components
│   ├── pages/             # Application pages
│   ├── utils/             # Helper utilities
│
└── README.md
🎯 Usage Examples
🔹 Quick Diagram Mode
Enter GitHub repository URL

Select required diagram type

Click Generate → View → Download

🔹 Chat Mode Examples
Ask questions like:

"Show authentication flow"

"Visualize database schema"

"Generate class hierarchy diagram"

"Explain backend architecture"

"Show API request lifecycle"

🔧 Environment Variables
env
Copy code
OPENAI_API_KEY=your_openai_api_key
GITHUB_TOKEN=your_github_token

🐛 Troubleshooting
Backend not starting → Check .env and dependencies

Frontend not showing data → Verify backend URL

Mermaid diagram blank → Mermaid syntax error

GitHub API rate limit exceeded → Add GitHub token

---------------------------------------------------------------------------------------------------------------

## 📄 License

This project is protected under a restrictive license.
The source code is shared for viewing and evaluation purposes only.
Any reuse or commercial use requires explicit permission.

