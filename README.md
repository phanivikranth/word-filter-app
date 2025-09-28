# Word Filter Application

[![CI/CD](https://github.com/phanivikranth/word-filter-app/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/phanivikranth/word-filter-app/actions/workflows/ci-cd.yml)
[![Release](https://github.com/phanivikranth/word-filter-app/actions/workflows/release.yml/badge.svg)](https://github.com/phanivikranth/word-filter-app/actions/workflows/release.yml)
[![License](https://img.shields.io/github/license/phanivikranth/word-filter-app)](LICENSE)
[![Docker Backend](https://img.shields.io/docker/v/phanivikranth/word-filter-backend?label=backend%20image)](https://hub.docker.com/r/phanivikranth/word-filter-backend)
[![Docker Frontend](https://img.shields.io/docker/v/phanivikranth/word-filter-frontend?label=frontend%20image)](https://hub.docker.com/r/phanivikranth/word-filter-frontend)

A full-stack web application for filtering words and solving word puzzles, built with FastAPI backend and Angular frontend. 

🌍 **Multi-Cloud Ready**: Deploy to AWS, Civo, or both simultaneously with full infrastructure automation and CI/CD support.

## Features

### **Filter Words Tab**
- **Advanced Word Filtering**: Filter words by:
  - Letters contained in the word
  - Starting letters
  - Ending letters
  - Exact word length
  - Minimum/Maximum word length
  - Result limit
- **Real-time Search**: Results update as you type
- **Word Statistics**: Display total words, length range, and average length

### **Interactive Word Puzzle Tab**
- **Word Puzzle Solver**: Enter known letters in specific positions
- **Dynamic Interface**: Input boxes adjust based on word length
- **Pattern Matching**: Find all words that match your partial pattern
- **Visual Feedback**: Clean, intuitive letter input boxes

### **Modern UI**
- **Tabbed Interface**: Easy navigation between features  
- **Responsive Design**: Works on desktop and mobile
- **Professional Styling**: Clean, modern design with smooth animations

## Project Structure

```
fullstack-app/
├── backend/           # FastAPI backend
│   ├── main.py       # Main FastAPI application
│   ├── requirements.txt
│   └── words.txt     # Word database
└── frontend/         # Angular frontend
    ├── src/
    │   ├── app/
    │   │   ├── components/
    │   │   ├── services/
    │   │   └── models/
    │   ├── index.html
    │   └── styles.css
    ├── package.json
    └── angular.json
```

## Setup Instructions

### Backend Setup (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   ```bash
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Add your words to `words.txt` (one word per line) or use the provided sample words.

6. Start the FastAPI server:
   ```bash
   python main.py
   ```
   
   The API will be available at `http://localhost:8001`
   - API Documentation: `http://localhost:8001/docs`

### Frontend Setup (Angular)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Start the Angular development server:
   ```bash
   npm start
   ```
   
   The application will be available at `http://localhost:4201`

## API Endpoints

### GET /words
Filter words based on various criteria.

**Query Parameters:**
- `contains` (string): Letters the word should contain
- `starts_with` (string): Letters the word should start with
- `ends_with` (string): Letters the word should end with
- `min_length` (int): Minimum word length
- `max_length` (int): Maximum word length
- `exact_length` (int): Exact word length
- `limit` (int): Maximum number of results (default: 100)

**Example:**
```
GET /words?contains=app&min_length=5&limit=10
```

### GET /words/stats
Get statistics about the word collection.

**Response:**
```json
{
  "total_words": 46,
  "min_length": 3,
  "max_length": 12,
  "avg_length": 7.5
}
```

### GET /words/by-length/{length}
Get all words of a specific length.

## Usage Examples

### **Filter Words Tab**
1. **Find all words containing "app":**
   - Enter "app" in the "Contains Letters" field

2. **Find 5-letter words:**
   - Enter "5" in the "Exact Length" field

3. **Find words starting with "a" and ending with "e":**
   - Enter "a" in "Starts With"
   - Enter "e" in "Ends With"

4. **Find words between 6-10 letters:**
   - Enter "6" in "Min Length"
   - Enter "10" in "Max Length"

### **Interactive Word Puzzle Tab**
1. **Solve a crossword clue (4-letter word, 2nd letter is 'A', last letter is 'E'):**
   - Enter "4" in "Expected Word Length"
   - Leave box 1 empty
   - Type "A" in box 2  
   - Leave box 3 empty
   - Type "E" in box 4
   - Click "Find Words" → Results: BALE, CAGE, CAKE, CAME, CAPE, etc.

2. **Find words with known middle letters:**
   - Enter "6" for length
   - Leave boxes 1, 2 empty
   - Type "R" in box 3
   - Type "I" in box 4  
   - Leave boxes 5, 6 empty
   - Results show all 6-letter words with "RI" in positions 3-4

## Customization

### Adding Your Own Words

Replace the contents of `backend/words.txt` with your own word list (one word per line):

```
your_word_1
your_word_2
your_word_3
...
```

### Styling

Modify `frontend/src/app/app.component.css` and `frontend/src/styles.css` to customize the appearance.

## 🌍 Multi-Cloud Deployment

Deploy your Word Filter App to multiple cloud providers with full automation:

### ☁️ Supported Cloud Providers
- **AWS**: EKS clusters with S3 storage
- **Civo**: Kubernetes clusters with Object Store
- **Multi-Cloud**: Deploy to both simultaneously

### 🚀 Quick Deployment
```bash
# Deploy to Civo (cost-effective, developer-friendly)
./scripts/civo/deploy-to-civo.sh -e prod -t full

# Deploy to AWS (enterprise-ready)
./scripts/aws/deploy-to-aws.sh -e prod -t full

# Deploy to both clouds
./scripts/deploy-multi-cloud.ps1 -CloudProvider both -Environment prod
```

### 💰 Cost Comparison
| Cloud | Minimal Setup | Full Production | Enterprise Scale |
|-------|---------------|-----------------|------------------|
| **Civo** | ~$11/month | ~$75/month | ~$150/month |
| **AWS** | ~$50/month | ~$200/month | ~$500/month |

### 📋 Deployment Options
- **Minimal**: Single node, local storage (~$11/month on Civo)
- **Full**: Multi-node, load balancers, monitoring
- **ObjectStore**: Optimized for large word datasets

See [CIVO_DEPLOYMENT.md](CIVO_DEPLOYMENT.md) and [AWS_SETUP.md](AWS_SETUP.md) for detailed guides.

## Technologies Used

- **Backend**: FastAPI, Python, Uvicorn
- **Frontend**: Angular, TypeScript, RxJS
- **Styling**: CSS Grid, Flexbox, CSS Variables
- **HTTP Client**: Angular HttpClient
- **CI/CD**: GitHub Actions, Docker, Dependabot
- **Testing**: pytest, Karma/Jasmine, Coverage reporting
- **Cloud**: AWS EKS, Civo Kubernetes, Multi-cloud support
- **Storage**: S3, Civo Object Store, Local files
- **Infrastructure**: Terraform, Kubernetes, Docker

## Development

Both servers support hot reload:
- FastAPI: Automatically reloads when Python files change
- Angular: Automatically reloads when TypeScript/HTML/CSS files change

## CI/CD Pipeline

This project includes a comprehensive CI/CD pipeline with GitHub Actions:

### 🔄 Automated Testing
- **Backend**: pytest with coverage reporting
- **Frontend**: Karma/Jasmine with Angular testing utilities
- **Integration**: End-to-end API testing
- **Security**: Dependency vulnerability scanning

### 🚀 Automated Deployment
- **Docker**: Automatic image building and publishing
- **Releases**: Tagged releases with changelog generation
- **Dependencies**: Automated dependency updates with Dependabot

### 📋 Quality Assurance
- **Code Linting**: Python (black, flake8, isort) and TypeScript (ESLint)
- **PR Validation**: Conventional commit format checking
- **Security Scanning**: Trivy vulnerability scanner

### 🔧 Getting Started with CI/CD
1. Fork the repository
2. Add required secrets (see `.github/README.md`)
3. Push changes to trigger automated testing
4. Create PRs for automatic validation
5. Tag releases (`v1.0.0`) for automated deployment

For detailed CI/CD documentation, see [`.github/README.md`](.github/README.md).

## Troubleshooting

1. **CORS Issues**: Make sure the FastAPI server is running on port 8001
2. **Connection Refused**: Ensure both servers are running
3. **No Words Found**: Check that `words.txt` exists and contains words
4. **Port Conflicts**: Modify ports in the configuration if needed
