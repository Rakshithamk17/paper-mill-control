# Deployment Guide

## Quick Start (Development)

```bash
./setup.sh
```

Then in two terminals:

```bash
# Terminal 1
cd backend && uvicorn main:app --reload

# Terminal 2
cd frontend && npm start
```

Access: http://localhost:3000

---

## Production Deployment

### Backend (Python/FastAPI)

**Option 1: systemd service**

Create `/etc/systemd/system/paper-mill-api.service`:

```ini
[Unit]
Description=Paper Mill Control System API
After=network.target

[Service]
Type=notify
User=mill-api
WorkingDirectory=/opt/paper-mill-control/backend
ExecStart=/opt/paper-mill-control/venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 main:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Start:
```bash
sudo systemctl start paper-mill-api
sudo systemctl enable paper-mill-api
```

**Option 2: Docker**

```dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY backend/ .

EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "main:app"]
```

Build & run:
```bash
docker build -t paper-mill-api .
docker run -d -p 8000:8000 paper-mill-api
```

### Frontend (React/Node)

**Option 1: Static deployment**

```bash
cd frontend
npm run build
```

Serve build/ directory with nginx:

```nginx
server {
    listen 80;
    server_name mill-dashboard.local;
    
    location / {
        root /opt/paper-mill-control/frontend/build;
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

**Option 2: Node.js with PM2**

```bash
cd frontend
npm install -g pm2 serve
serve -s build -l 3000 &
```

**Option 3: Docker**

```dockerfile
# Build stage
FROM node:18-alpine as builder
WORKDIR /app
COPY frontend/package.json .
RUN npm install
COPY frontend/ .
RUN npm run build

# Serve stage
FROM node:18-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/build .
EXPOSE 3000
CMD ["serve", "-s", ".", "-l", "3000"]
```

### Database

**Backup**
```bash
cp backend/data/control_system.db backend/data/control_system.db.backup
```

**Migration** (if schema changes)
```bash
python3 backend/database.py  # Adds new tables if needed
```

---

## Environment Variables

**Backend (.env)**
```
FLASK_ENV=production
DATABASE_URL=sqlite:///backend/data/control_system.db
SECRET_KEY=your-secret-key
LOG_LEVEL=INFO
```

**Frontend (.env)**
```
REACT_APP_API_URL=https://api.mill-control.local
REACT_APP_ENV=production
```

---

## Monitoring

### Logs

**Backend**
```bash
tail -f /var/log/paper-mill-api.log
```

**Frontend**
```bash
tail -f /var/log/paper-mill-dashboard.log
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Stats
curl http://localhost:8000/stats
```

### Database Size

```bash
ls -lh backend/data/control_system.db
```

---

## Performance Tuning

**Backend**
- Increase workers: `gunicorn -w 8` (2x CPU cores)
- Enable caching: Add Redis for model predictions
- Connection pooling: SQLAlchemy with pool_size=20

**Frontend**
- Enable gzip compression in nginx
- Use CDN for Recharts library
- Lazy load panels not in viewport

---

## Security

- [ ] Enable HTTPS (Let's Encrypt)
- [ ] API rate limiting (FastAPI Limiter)
- [ ] Database encryption at rest
- [ ] API key authentication (optional)
- [ ] CORS properly configured
- [ ] Input validation on all endpoints

---

## Troubleshooting

**Backend won't start**
```bash
# Check database
python3 backend/database.py

# Check models trained
ls -la backend/models/
```

**Frontend won't connect**
```bash
# Check API URL in .env
echo $REACT_APP_API_URL

# Test API directly
curl http://localhost:8000/health
```

**Models not trained**
```bash
# Generate data and train
python3 backend/data_generator.py
python3 backend/models.py
```

---

## Scaling

For multi-mill deployment:
1. One API instance per mill (separate DBs)
2. Shared frontend with mill selector
3. Load balancer (nginx) distributing requests
4. Centralized logging (ELK stack)

---

## Updates

```bash
# Pull latest
git pull origin main

# Reinstall deps (if changed)
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..

# Retrain models (if code changed)
python3 backend/models.py

# Rebuild frontend
cd frontend && npm run build && cd ..

# Restart services
sudo systemctl restart paper-mill-api
```
