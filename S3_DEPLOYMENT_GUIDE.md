# 🚀 EKS Deployment with S3 Integration

## 📋 **Current Setup vs S3 Setup**

### **❌ Current Setup (Static)**
```
Docker Container → words.txt (baked into image) → Memory
```
**Problems:**
- Words file is **baked into Docker image**
- **Can't update words** without rebuilding container
- Each pod has **separate word list** 
- **Lost when pods restart**

### **✅ S3 Setup (Dynamic)**
```
S3 Bucket → words.txt → Multiple Pods → Shared Memory
```
**Benefits:**
- **Dynamic word updates** via API
- **Shared word list** across all pods
- **Persistent storage** with versioning
- **No container rebuilds** needed

---

## 🏗️ **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────┐
│                     EKS Cluster                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │   Frontend Pod  │    │   Backend Pod 1 │◄─────────┐     │
│  │   (Angular)     │    │   (FastAPI)     │          │     │
│  └─────────────────┘    └─────────────────┘          │     │
│           │                       │                   │     │
│           │              ┌─────────────────┐          │     │
│           │              │   Backend Pod 2 │◄─────────┤     │
│           │              │   (FastAPI)     │          │     │
│           │              └─────────────────┘          │     │
│           │                       │                   │     │
│           └───────────────────────┼───────────────────┘     │
│                                   │                         │
└───────────────────────────────────┼─────────────────────────┘
                                    │
                            ┌───────▼───────┐
                            │   S3 Bucket   │
                            │ word-filter-  │
                            │   storage     │
                            │               │
                            │ words/        │
                            │ words.txt     │
                            └───────────────┘
```

---

## 📦 **What Gets Deployed Where**

### **Docker Container Contents:**
```
/app/
├── main.py              # FastAPI app with S3 integration
├── word_manager.py      # S3 word management logic
├── requirements.txt     # Python deps (includes boto3)
└── words.txt           # Local fallback file
```

### **S3 Bucket Structure:**
```
s3://word-filter-storage-{timestamp}/
└── words/
    └── words.txt       # Master word list (updateable)
```

### **Kubernetes Resources:**
```
word-filter-app/
├── ConfigMap          # S3 bucket configuration
├── Secret             # AWS credentials
├── Backend Pods       # FastAPI with S3 integration
├── Frontend Pods      # Angular (unchanged)
└── Services/Ingress   # Load balancing
```

---

## 🚀 **Quick Deployment**

### **Option 1: Automated Setup**
```bash
# Run the complete setup script
chmod +x scripts/setup-s3-deployment.sh
./scripts/setup-s3-deployment.sh
```

### **Option 2: Manual Setup**

#### **1. Create S3 Bucket**
```bash
aws s3 mb s3://word-filter-storage-$(date +%s) --region us-west-2
```

#### **2. Upload Initial Words**
```bash
aws s3 cp backend/words.txt s3://your-bucket/words/words.txt
```

#### **3. Update Kubernetes Config**
```bash
# Update bucket name in k8s-s3/configmap.yaml
sed -i 's/word-filter-storage/your-actual-bucket-name/g' k8s-s3/configmap.yaml
```

#### **4. Deploy**
```bash
kubectl apply -f k8s-s3/
```

---

## 🔧 **Configuration**

### **Environment Variables (ConfigMap):**
```yaml
WORDS_S3_BUCKET: "word-filter-storage"    # Your S3 bucket name
WORDS_S3_KEY: "words/words.txt"           # Path to words file in S3
AWS_REGION: "us-west-2"                   # AWS region
```

### **AWS Credentials (Secret):**
```yaml
AWS_ACCESS_KEY_ID: "<base64-encoded>"
AWS_SECRET_ACCESS_KEY: "<base64-encoded>"
```

### **Better: Use IAM Roles (IRSA)**
Instead of hardcoded credentials, use IAM Roles for Service Accounts:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: word-filter-backend
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::YOUR-ACCOUNT:role/WordFilterS3Role
```

---

## 📝 **API Endpoints for Word Management**

### **Add Single Word**
```bash
curl -X POST http://your-app-url/words/add \
     -H "Content-Type: application/json" \
     -d '{"word":"amazing"}'
```

### **Add Multiple Words**
```bash
curl -X POST http://your-app-url/words/add-batch \
     -H "Content-Type: application/json" \
     -d '{"words":["fantastic","incredible","awesome"]}'
```

### **Check if Word Exists**
```bash
curl -X POST http://your-app-url/words/check \
     -H "Content-Type: application/json" \
     -d '{"word":"test"}'
```

### **Reload Words from S3**
```bash
curl -X POST http://your-app-url/words/reload
```

### **Get All Words (Admin)**
```bash
curl http://your-app-url/words/all?limit=100
```

---

## 🔄 **Dynamic Word Updates Workflow**

### **When You Add a Word:**

1. **User calls API:** `POST /words/add`
2. **Backend validates:** Word is alphabetic and not duplicate
3. **Update memory:** Add to local `words_set`
4. **Save to S3:** Update `s3://bucket/words/words.txt`
5. **All pods sync:** Next API call loads updated list
6. **Response:** Success confirmation with word count

### **How Pods Stay in Sync:**
- Each API call may trigger a **fresh S3 load**
- Background **periodic sync** (optional)
- **Shared S3 storage** ensures consistency
- **Automatic fallback** to local file if S3 fails

---

## 💰 **Cost Implications**

### **S3 Storage Costs:**
- **Words file:** ~1-10 KB (negligible)
- **Requests:** ~$0.0004 per 1,000 requests
- **Monthly cost:** < $1 for typical usage

### **EKS Costs:**
- **Control Plane:** $73/month (unchanged)
- **EC2 Nodes:** Same as before
- **Additional:** Minimal S3 costs

### **Benefits:**
- ✅ **No container rebuilds** (saves time & compute)
- ✅ **Dynamic scaling** without data loss
- ✅ **Shared state** across replicas
- ✅ **Backup & versioning** included

---

## 🛡️ **Security Best Practices**

### **1. IAM Roles (Recommended)**
```bash
# Create IAM role for EKS service account
aws iam create-role --role-name WordFilterS3Role \
    --assume-role-policy-document file://trust-policy.json

# Attach S3 policy
aws iam attach-role-policy \
    --role-name WordFilterS3Role \
    --policy-arn arn:aws:iam::ACCOUNT:policy/WordFilterS3Policy
```

### **2. S3 Bucket Security**
```bash
# Block public access
aws s3api put-public-access-block --bucket your-bucket \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Enable versioning
aws s3api put-bucket-versioning --bucket your-bucket \
    --versioning-configuration Status=Enabled
```

### **3. Kubernetes Secrets**
```bash
# Don't commit credentials to Git
# Use external secret management (AWS Secrets Manager, Vault)
# Rotate credentials regularly
```

---

## 🔍 **Monitoring & Troubleshooting**

### **Check S3 Integration:**
```bash
# Check pod logs
kubectl logs -f deployment/word-filter-backend -n word-filter-app

# Check health endpoint
kubectl port-forward service/word-filter-backend 8001:8001 -n word-filter-app
curl http://localhost:8001/health
```

### **Common Issues:**

#### **❌ "No S3 client available"**
**Problem:** AWS credentials not configured
**Solution:**
```bash
# Check secret exists
kubectl get secret word-filter-aws-credentials -n word-filter-app

# Verify credentials are valid
aws sts get-caller-identity
```

#### **❌ "Bucket does not exist"**
**Problem:** S3 bucket not created or wrong name
**Solution:**
```bash
# Check bucket exists
aws s3 ls s3://your-bucket-name

# Update ConfigMap with correct bucket name
kubectl edit configmap word-filter-config -n word-filter-app
```

#### **❌ "Access Denied"**
**Problem:** IAM permissions insufficient
**Solution:**
```bash
# Check IAM policy allows s3:GetObject, s3:PutObject, s3:ListBucket
# Verify credentials have access to the specific bucket
```

---

## 🎯 **Migration from Static to S3**

### **Step 1: Backup Current Words**
```bash
kubectl exec deployment/word-filter-backend -n word-filter-app -- cat words.txt > current-words.txt
```

### **Step 2: Deploy S3 Version**
```bash
./scripts/setup-s3-deployment.sh
```

### **Step 3: Upload Your Words**
```bash
aws s3 cp current-words.txt s3://your-bucket/words/words.txt
```

### **Step 4: Test & Verify**
```bash
curl http://your-app-url/words/stats
# Should show your word count
```

---

## 🚀 **Production Recommendations**

### **1. Use IAM Roles instead of Access Keys**
### **2. Enable S3 versioning for backup**
### **3. Set up CloudWatch monitoring**
### **4. Use multiple availability zones**
### **5. Implement proper logging**
### **6. Add rate limiting for word additions**

---

## 📊 **Comparison Summary**

| Feature | Static (Current) | S3 Integration |
|---------|------------------|----------------|
| **Word Updates** | ❌ Rebuild container | ✅ API call |
| **Pod Sync** | ❌ Separate lists | ✅ Shared S3 |
| **Persistence** | ❌ Lost on restart | ✅ Permanent |
| **Scalability** | ❌ Limited | ✅ Unlimited |
| **Backup** | ❌ Manual | ✅ Automatic |
| **Cost** | Lower | Slightly higher |
| **Complexity** | Simple | Moderate |

---

## 🎉 **Result**

With S3 integration, your Word Filter App becomes a **truly dynamic, scalable application** where:

- ✅ **Users can add words** via the web interface
- ✅ **Words persist** across pod restarts  
- ✅ **All pods share** the same word list
- ✅ **No downtime** for word updates
- ✅ **Professional architecture** ready for production

**Your `words.txt` now lives in S3 and can be updated dynamically without any container rebuilds!** 🚀
