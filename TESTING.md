# 🧪 Minimal Testing Setup Guide

Perfect for testing your Word Filter App without breaking the bank! Here are your options from **FREE** to **minimal cost**.

## 🆓 **Option 1: Docker Compose (Recommended for Testing)**

**Cost:** FREE  
**Setup Time:** 2 minutes  
**Requirements:** Docker Desktop only

### Quick Start:
```bash
# One command to rule them all!
chmod +x scripts/test-deploy.sh
./scripts/test-deploy.sh 1

# Or manually:
docker-compose -f docker-compose.test.yml up --build
```

### Access Your App:
- **Full App**: http://localhost
- **API Only**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

### Stop Testing:
```bash
docker-compose -f docker-compose.test.yml down
```

---

## 🏠 **Option 2: Kind (Local Kubernetes)**

**Cost:** FREE  
**Setup Time:** 5 minutes  
**Requirements:** Docker + Kind

### Install Kind:
```bash
# Linux
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind

# Windows (Chocolatey)
choco install kind

# macOS
brew install kind
```

### Deploy:
```bash
./scripts/test-deploy.sh 2
```

### Access Your App:
- **Full App**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs

### Cleanup:
```bash
kind delete cluster --name word-filter-test
```

---



## 🏠 **Option 3: Development Mode (No Containers)**

**Cost:** FREE  
**Setup Time:** 30 seconds  
**Requirements:** Nothing new

### Start:
```bash
./scripts/test-deploy.sh 3

# Or manually:
# Terminal 1: cd backend && ./venv/Scripts/activate && python main.py  
# Terminal 2: cd frontend && npm start
```

### Access:
- **Full App**: http://localhost:4201

---

## 📊 **Comparison Table**

| Method | Cost | Setup | Kubernetes | Production-Like | Internet Access |
|--------|------|-------|------------|----------------|----------------|
| **Docker Compose** | FREE | ⭐⭐⭐⭐⭐ | ❌ | ⭐⭐⭐ | ❌ |
| **Kind** | FREE | ⭐⭐⭐⭐ | ✅ | ⭐⭐⭐⭐ | ❌ |
| **Dev Mode** | FREE | ⭐⭐⭐⭐⭐ | ❌ | ⭐⭐ | ❌ |

---

## 🎯 **Recommended Testing Flow**

### 1. **Start with Docker Compose**
- Test basic functionality
- Verify containers work
- Debug any issues

### 2. **Try Kind for Kubernetes**
- Test Kubernetes manifests
- Verify ingress routing
- Practice kubectl commands

---

## 📁 **File Structure for Testing**

```
fullstack-app/
├── docker-compose.test.yml      # Docker Compose setup
├── nginx-local.conf             # Local nginx config
├── kind-config.yaml             # Kind cluster config
└── scripts/
    └── test-deploy.sh           # Automated deployment script
```

---

## 🔧 **Resource Requirements**

### Docker Compose:
- **RAM**: 1GB total
- **CPU**: Minimal
- **Storage**: ~500MB

### Kind:
- **RAM**: 2GB total  
- **CPU**: 1-2 cores
- **Storage**: ~1GB

---

## 🐛 **Troubleshooting**

### Docker Issues:
```bash
# Check container logs
docker-compose -f docker-compose.test.yml logs backend
docker-compose -f docker-compose.test.yml logs frontend

# Restart services
docker-compose -f docker-compose.test.yml restart
```

### Kind Issues:
```bash
# Check pod status
kubectl get pods -n word-filter-test

# Check pod logs
kubectl logs deployment/word-filter-backend -n word-filter-test

# Debug ingress
kubectl describe ingress word-filter-ingress -n word-filter-test
```

---

## 🎉 **Quick Test Commands**

Once your app is running, test these endpoints:

```bash
# Health check
curl http://localhost/

# Get word stats
curl http://localhost/words/stats

# Search for words containing "app"
curl "http://localhost/words?contains=app&limit=5"

# Interactive word puzzle (5-letter words with 'A' as 2nd letter)
curl "http://localhost/words/interactive?length=5&pattern=?A???"
```

---

## 💡 **Tips for Testing**

1. **Start Simple**: Use Docker Compose first
2. **Test Incrementally**: One feature at a time
3. **Use Logs**: Check container/pod logs for issues
4. **Monitor Resources**: Watch CPU/memory usage

---

## 🚀 **Ready to Test?**

```bash
# Choose your adventure:
chmod +x scripts/test-deploy.sh
./scripts/test-deploy.sh

# Or jump right in with Docker Compose:
docker-compose -f docker-compose.test.yml up --build
```

**Your app will be ready for testing in minutes, not hours!** 🎯
