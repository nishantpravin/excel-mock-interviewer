# 📊 Excel Mock Interviewer

> **Live Demo:** [Streamlit app](ai-excel-mock-interviewer.streamlit.app) | **Repository:** [GitHub](https://github.com/nishantpravin/excel-mock-interviewer)

An intelligent AI-powered mock interviewer that conducts structured Excel interviews, provides real-time evaluation, adaptive hints, and generates comprehensive performance reports. Perfect for job seekers preparing for Excel-focused roles or recruiters looking to standardize their interview process.

---

## 🌟 Key Features

### 🎯 **Intelligent Interview Conductor**
- **Structured Multi-Turn Flow**: Introduction → Adaptive Questions → Summary & Feedback
- **Dynamic Question Selection**: Non-repetitive questions based on difficulty progression
- **Real-time Typing Animation**: Mimics human interviewer for authentic experience
- **Interactive Commands**: Support for `skip`, `hint`, and question clarification

### 🧠 **Hybrid Evaluation System**
- **Deterministic Scoring**: Keyword and phrase matching using RapidFuzz for consistent baseline evaluation
- **LLM-Enhanced Assessment**: Optional OpenAI API integration for deeper semantic understanding
- **Multi-Dimensional Scoring**: 
  - **Accuracy** (38%): Correctness of technical details
  - **Completeness** (30%): Coverage of key concepts
  - **Clarity** (18%): Communication effectiveness
  - **Depth** (14%): Advanced understanding demonstration

### 📈 **Comprehensive Reporting**
- **Real-time Feedback**: Instant per-question scoring with detailed breakdowns
- **Performance Banding**: Dynamic skill level assessment (Beginner → Intermediate → Advanced)
- **Export Options**: 
  - 📄 **PDF Reports**: Professional summary with charts and recommendations
  - 📊 **CSV Transcripts**: Detailed question-answer logs for analysis
  - 📈 **Score Trends**: Visual performance tracking across questions

### ⚡ **Advanced State Management**
- **Agentic Architecture**: Intelligent question flow management
- **Session Persistence**: Maintains context throughout the interview
- **Timer Integration**: Per-question time tracking for realistic pressure
- **Adaptive Difficulty**: Questions adjust based on previous performance

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | Streamlit | Interactive web interface |
| **AI/LLM** | OpenAI GPT-4o-mini | Semantic evaluation & dialog |
| **Text Processing** | RapidFuzz | Fuzzy string matching for keywords |
| **Data Export** | ReportLab, Pandas | PDF generation and CSV exports |
| **Deployment** | Streamlit Community Cloud | Hosted application |

---

## 📁 Project Architecture

```
ai-excel-mock-interviewer/
├── 🎯 src/
│   ├── app.py              # Main Streamlit application
│   ├── bank.py             # Question bank management
│   ├── evaluator.py        # Hybrid scoring engine
│   ├── dialog.py           # LLM integration & prompts
│   └── report.py           # PDF/CSV report generation
├── 📊 data/
│   └── question_bank.json  # Curated Excel questions database
├── 📚 docs/
│   ├── DesignDocument.md   # Technical specifications
│   └── sample_transcripts/ # Example outputs
├── ⚙️ requirements.txt     # Python dependencies
├── 🔧 .env.example         # Environment configuration template
└── 📖 README.md            # This file
```

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.8+ installed
- Git for cloning the repository
- Optional: OpenAI API key for enhanced LLM features

### 1️⃣ **Clone & Setup**
```bash
# Clone the repository
git clone https://github.com/nishantpravin/excel-mock-interviewer.git
cd excel-mock-interviewer

# Create virtual environment
python -m venv .venv

# Activate environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 2️⃣ **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 3️⃣ **Configure Environment**

Create a `.env` file or configure through Streamlit secrets:

```ini
# Application Settings
APP_NAME=Excel Mock Interviewer
NUM_QUESTIONS=7
DETERMINISTIC_ONLY=true

# Optional: Enhanced LLM Features
# OPENAI_API_KEY=sk-your-api-key-here
# LLM_MODEL=gpt-4o-mini

# Scoring Configuration
W_ACC=0.38          # Accuracy weight
W_COMP=0.30         # Completeness weight  
W_CLAR=0.18         # Clarity weight
W_DEPTH=0.14        # Depth weight
KW_HIT_THRESHOLD=68 # Keyword matching sensitivity
```

### 4️⃣ **Launch Application**
```bash
streamlit run src/app.py
```

The application will be available at `http://localhost:8501`

---

## 💡 Usage Examples

### **Basic Interview Flow**
1. **Start Interview**: Click "Begin Interview" to initialize
2. **Answer Questions**: Respond naturally to Excel-related questions
3. **Use Commands**: 
   - Type `hint` for guidance
   - Type `skip` to move to next question
   - Ask for clarification anytime
4. **Review Results**: Get instant feedback and final performance report
5. **Download Reports**: Export PDF summary and CSV transcript

### **Sample Question Types**
- **Basic**: "How do you create a pivot table in Excel?"
- **Intermediate**: "Explain the difference between VLOOKUP and INDEX-MATCH"
- **Advanced**: "How would you optimize a workbook with performance issues?"

---

## 📊 Sample Output

### **Real-time Feedback**
```
Question 3/7: VLOOKUP vs INDEX-MATCH

Your Answer: "VLOOKUP searches left to right, INDEX-MATCH is more flexible..."

📊 Scores:
├── Accuracy: 85% ✅
├── Completeness: 78% ✅  
├── Clarity: 92% ✅
└── Depth: 70% ⚠️

💡 Feedback: Great explanation of basic differences! Consider mentioning 
performance implications and array formula compatibility.

Overall Score: 81% (Intermediate Level)
```

### **Final Report Features**
- 📈 **Performance Trend Chart**: Score progression across questions
- 🎯 **Skill Assessment**: Current proficiency level with recommendations
- 📝 **Detailed Transcript**: Complete Q&A log with timestamps
- 🚀 **Improvement Areas**: Targeted suggestions for skill development

---

## 🌐 Deployment

### **Streamlit Community Cloud** (Recommended)
1. Fork this repository to your GitHub account
2. Connect your GitHub account to [Streamlit Cloud](https://streamlit.io/cloud)
3. Deploy from your forked repository
4. Configure secrets in the Streamlit dashboard under **Settings → Secrets**

### **Local Production**
```bash
# Install production dependencies
pip install -r requirements.txt

# Run with production settings
streamlit run src/app.py --server.port 8501 --server.address 0.0.0.0
```

### **Docker Deployment**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "src/app.py"]
```

---

## 🔧 Advanced Configuration

### **Question Bank Customization**
Edit `data/question_bank.json` to add custom questions:
```json
{
  "beginner": [
    {
      "question": "Your custom question here",
      "keywords": ["key", "terms", "for", "evaluation"],
      "difficulty": 1,
      "category": "formulas"
    }
  ]
}
```

### **Scoring Algorithm Tuning**
Modify weights in your environment configuration:
- Increase `W_ACC` for technical accuracy focus
- Increase `W_CLAR` for communication skills emphasis
- Adjust `KW_HIT_THRESHOLD` for keyword sensitivity

### **LLM Integration**
Enable enhanced semantic evaluation:
```ini
DETERMINISTIC_ONLY=false
OPENAI_API_KEY=your-api-key
LLM_MODEL=gpt-4o-mini
```

---

## 🧪 Testing & Development

### **Run Tests**
```bash
# Unit tests
python -m pytest tests/

# Integration tests
python -m pytest tests/integration/

# Coverage report
pytest --cov=src tests/
```

### **Development Mode**
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run with auto-reload
streamlit run src/app.py --server.runOnSave true
```

---



## 📞 Support & Contact

- 🐛 **Issues**: [GitHub Issues](https://github.com/nishantpravin/excel-mock-interviewer/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/nishantpravin/excel-mock-interviewer/discussions)
- 📧 **Contact**: [Email](mailto:ndubey1245@gmail.com)
- 🔗 **LinkedIn**: [Nishant Dubey](https://www.linkedin.com/in/nishant-dubey-466656191/)

---

<div align="center">



*Built with ❤️ and efforts hope you guys will like it *

</div>