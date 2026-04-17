# ShikshaGuard - BAV System

A comprehensive **Budget Allocation & Validation (BAV) System** for educational institutions. ShikshaGuard leverages AI/ML and rule-based validation to help schools optimize budget allocation, forecast infrastructure needs, and identify financial anomalies.

## 🎯 Overview

ShikshaGuard is an intelligent decision-support system designed to:
- **Validate** budget proposals using ML models and business rules
- **Forecast** enrollment trends and infrastructure requirements
- **Identify** anomalies and financial risks
- **Simulate** budget scenarios for strategic planning
- **Provide** AI-powered insights and recommendations

## ✨ Key Features

### 1. **Proposal Validation**
- Multi-stage validation pipeline (ML + Rules + AI)
- Risk scoring and anomaly detection
- Automated flagging of suspicious patterns
- Explainable predictions using SHAP values

### 2. **Forecasting Engine**
- Enrollment forecasting using XGBoost
- Infrastructure need projections
- Time-series analysis capabilities
- Seasonal trend detection

### 3. **Risk Assessment**
- Anomaly detection using Isolation Forest
- Financial risk scoring
- Budget constraint validation
- Multi-factor risk analysis

### 4. **Strategic Planning**
- Scenario simulation capabilities
- What-if analysis tools
- Budget optimization suggestions
- Data-driven planning support

### 5. **Dashboard & Analytics**
- Real-time analytics dashboard
- School profile management
- Proposal tracking and history
- District-level aggregated statistics

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn
- **Database**: SQLAlchemy with SQLite
- **ML/AI**: 
  - scikit-learn (Random Forest, Isolation Forest)
  - XGBoost (Forecasting)
  - SHAP (Model interpretability)
- **APIs**: OpenRouter (AI features)
- **Authentication**: JWT with python-jose & bcrypt
- **Rate Limiting**: SlowAPI

### Frontend
- **Framework**: React 19
- **Build Tool**: Vite
- **Routing**: React Router DOM v7
- **HTTP Client**: Axios
- **Icons**: Lucide React
- **Styling**: CSS

### Infrastructure
- **Migrations**: Alembic
- **Configuration**: Python dotenv
- **Package Management**: npm, pip

## 📁 Project Structure

```
ShikshaGuard/
├── BAV-System-main/                 # Backend application
│   ├── app/
│   │   ├── api/                     # API routes and endpoints
│   │   │   ├── main.py              # FastAPI application entry point
│   │   │   ├── auth/                # Authentication logic
│   │   │   └── routes/              # API endpoints
│   │   ├── database/                # Database models and setup
│   │   │   ├── db.py                # Database configuration
│   │   │   └── models.py            # SQLAlchemy models
│   │   ├── services/                # Business logic
│   │   │   ├── validation_service.py    # Proposal validation
│   │   │   ├── risk_service.py         # Risk assessment
│   │   │   ├── ai_service.py           # AI/OpenRouter integration
│   │   │   └── simulation_service.py    # Scenario simulation
│   │   ├── models/                  # ML models & training
│   │   │   ├── train.py             # Model training scripts
│   │   │   └── artifacts/           # Serialized models
│   │   ├── utils/                   # Utility functions
│   │   │   ├── feature_builder.py   # Feature engineering
│   │   │   └── rule_engine.py       # Business rule validation
│   │   └── data/                    # Data pipeline
│   │       ├── pipeline.py          # Data processing
│   │       └── *.csv                # Training datasets
│   ├── alembic/                     # Database migrations
│   ├── config.py                    # Configuration management
│   ├── requirements.txt             # Python dependencies
│   └── pyproject.toml               # Project configuration
│
├── frontend/                        # React frontend application
│   ├── src/
│   │   ├── pages/                   # Page components
│   │   │   ├── Dashboard.jsx        # Main dashboard
│   │   │   ├── ProposalForm.jsx     # Budget proposal form
│   │   │   ├── ProposalsList.jsx    # Proposals listing
│   │   │   ├── Forecaster.jsx       # Forecasting interface
│   │   │   ├── StrategicPlanning.jsx # Planning tools
│   │   │   ├── Login.jsx            # Authentication
│   │   │   ├── SchoolProfile.jsx    # School information
│   │   │   └── AiControlPanel.jsx   # AI insights panel
│   │   ├── api.js                   # API client configuration
│   │   ├── App.jsx                  # Main app component
│   │   ├── main.jsx                 # Entry point
│   │   └── styles/                  # CSS stylesheets
│   ├── public/                      # Static assets
│   ├── package.json                 # Frontend dependencies
│   └── vite.config.js               # Vite configuration
│
├── FEATURE_AUDIT_REPORT.md          # Feature documentation
└── README.md                        # This file
```

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 16+
- npm or yarn
- Git

### Backend Setup

1. **Clone the repository**
```bash
git clone https://github.com/Uttham68/ShikshaGuard.git
cd ShikshaGuard
```

2. **Navigate to backend directory**
```bash
cd BAV-System-main
```

3. **Create and activate virtual environment**
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

4. **Install dependencies**
```bash
pip install -r requirements.txt
```

5. **Set up environment variables**
Create a `.env` file in the `BAV-System-main` directory:
```env
DATABASE_URL=sqlite:///./shikshasgaurd.db
SECRET_KEY=your-secret-key-here
OPENROUTER_API_KEY=your-openrouter-api-key
CORS_ORIGINS=http://localhost:5173
RATE_LIMIT_PER_MINUTE=60
```

6. **Initialize database**
```bash
python -c "from app.database.db import init_db; init_db()"
```

7. **Start the backend server**
```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative Docs: `http://localhost:8000/redoc`

### Frontend Setup

1. **Navigate to frontend directory**
```bash
cd frontend
```

2. **Install dependencies**
```bash
npm install
```

3. **Start development server**
```bash
npm run dev
```

The application will be available at: `http://localhost:5173`

## 📚 API Documentation

### Key Endpoints

#### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/refresh` - Refresh token

#### Proposals
- `POST /proposal/submit` - Submit budget proposal
- `POST /proposal/validate` - Validate proposal
- `GET /proposal/{id}` - Get proposal details
- `GET /proposals` - List all proposals

#### Forecasting
- `POST /forecast` - Forecast enrollment/infrastructure

#### Risk Assessment
- `POST /risk-score` - Compute risk scores
- `GET /risk/anomalies` - List detected anomalies

#### Schools
- `GET /school/{pseudocode}` - Get school data
- `GET /schools` - List all schools
- `GET /dashboard` - Get aggregated statistics

### Example Request

```bash
curl -X POST "http://localhost:8000/proposal/validate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d {
    "school_id": 1,
    "budget_amount": 500000,
    "category": "infrastructure",
    "description": "New classroom construction"
  }
```

## 🤖 ML Models

### Trained Models

1. **Random Forest Validator** (`rf_validator.joblib`)
   - Validates proposal legitimacy
   - Features: Budget amount, category, school metrics
   - Output: Confidence score (0-1)

2. **XGBoost Forecaster** (`xgb_forecaster.joblib`)
   - Forecasts enrollment trends
   - Features: Historical enrollment, demographics
   - Output: Predicted enrollment

3. **Isolation Forest Anomaly Detector** (`iso_anomaly.joblib`)
   - Detects anomalies in proposals
   - Identifies unusual patterns
   - Output: Anomaly score

### Model Training

To retrain models with new data:

```bash
cd BAV-System-main
python app/models/train.py
```

## 📊 Database Schema

### Core Tables

- **Schools**: School information and baseline data
- **Proposals**: Budget proposals with metadata
- **ValidationResults**: Validation results and scores
- **Users**: System users and authentication
- **AnomalyLogs**: Detected anomalies

## 🔐 Security Features

- JWT-based authentication
- Password hashing with bcrypt
- Rate limiting (60 requests/minute default)
- CORS configuration
- SQL injection prevention via SQLAlchemy ORM
- Environment variable management

## 🧪 Testing

To run tests:
```bash
# Backend tests
cd BAV-System-main
pytest

# Frontend tests
cd frontend
npm test
```

## 📈 Performance Optimization

- Model caching with joblib
- Database query optimization
- Frontend bundle optimization with Vite
- API response pagination
- Rate limiting to prevent abuse

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Contributors

- **Uttham68** (GitHub: [@Uttham68](https://github.com/Uttham68))

## 📞 Support & Contact

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the [FEATURE_AUDIT_REPORT.md](./FEATURE_AUDIT_REPORT.md) for detailed feature documentation

## 🎓 System Architecture

```
┌─────────────────┐
│   React Frontend│
│  (Port: 5173)   │
└────────┬────────┘
         │
    Axios HTTP/REST
         │
┌─────────▼────────────────────────┐
│     FastAPI Backend              │
│      (Port: 8000)                │
├──────────────────────────────────┤
│  Routes → Services → Utils       │
│    ↓                             │
│  ┌─────────────────────────────┐ │
│  │  Validation Service         │ │
│  │  - ML Models (RF, XGBoost)  │ │
│  │  - Rule Engine              │ │
│  │  - Anomaly Detection        │ │
│  └─────────────────────────────┘ │
│    ↓                             │
│  ┌─────────────────────────────┐ │
│  │  Database (SQLAlchemy)      │ │
│  │  - Schools, Proposals       │ │
│  │  - Validation Results       │ │
│  │  - Users, Logs              │ │
│  └─────────────────────────────┘ │
│    ↓                             │
│  ┌─────────────────────────────┐ │
│  │  External Services          │ │
│  │  - OpenRouter (AI)          │ │
│  └─────────────────────────────┘ │
└──────────────────────────────────┘
```

## 🚢 Deployment

### Docker Support (Coming Soon)
```bash
docker-compose up
```

### Environment Variables for Production
- Set `DEBUG=False`
- Use production database (PostgreSQL recommended)
- Configure CORS for your domain
- Set strong `SECRET_KEY`
- Enable HTTPS

## 📦 Dependencies

### Backend Key Dependencies
- FastAPI 0.136.0
- Uvicorn 0.44.0
- SQLAlchemy 2.0.49
- scikit-learn 1.8.0
- XGBoost 3.2.0
- SHAP 0.51.0

### Frontend Key Dependencies
- React 19.2.4
- React Router 7.14.1
- Axios 1.15.0
- Vite 8.0.4

## 📅 Version History

- **v1.0.0** (2026-04-17) - Initial release with core features

---

**Last Updated**: April 17, 2026
