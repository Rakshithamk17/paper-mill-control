#!/bin/bash
# Complete setup script for Paper Mill Intelligent Process Control System

set -e

echo "=========================================="
echo "Paper Mill Control System - Setup Script"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Step 1: Creating directory structure...${NC}"
mkdir -p backend/data backend/models frontend/src/components frontend/public

echo -e "${BLUE}Step 2: Installing backend dependencies...${NC}"
cd backend
pip install -r requirements.txt
cd ..

echo -e "${BLUE}Step 3: Initializing database...${NC}"
python3 backend/database.py

echo -e "${BLUE}Step 4: Generating synthetic data (200 events)...${NC}"
python3 backend/data_generator.py

echo -e "${BLUE}Step 5: Processing events and extracting features...${NC}"
python3 backend/feature_engineering.py

echo -e "${BLUE}Step 6: Training ML models...${NC}"
python3 backend/models.py

echo -e "${BLUE}Step 7: Installing frontend dependencies...${NC}"
cd frontend
npm install
cd ..

echo -e "${GREEN}=========================================="
echo -e "✅ Setup Complete!${NC}"
echo -e "${GREEN}==========================================${NC}"

echo ""
echo "To start the system:"
echo ""
echo "Terminal 1 - Backend API:"
echo "  cd backend"
echo "  uvicorn main:app --reload"
echo ""
echo "Terminal 2 - Frontend Dashboard:"
echo "  cd frontend"
echo "  npm start"
echo ""
echo "Dashboard will be available at: http://localhost:3000"
echo "API documentation at: http://localhost:8000/docs"
echo ""
