# AKS Deployment Guide

## How It Works

### The Message Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   React      │     │   FastAPI    │     │   Service    │     │   Worker     │
│   Frontend   │────▶│   API Pod    │────▶│   Bus Queue  │────▶│   Pod        │
│              │     │              │     │              │     │              │
│ User clicks  │     │ POST /api/   │     │ Message      │     │ Polls queue  │
│ "Send"       │     │ send         │     │ waits here   │     │ continuously │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
      │                    │                    │                    │
      │                    │                    │                    │
      ▼                    ▼                    ▼                    ▼
   Browser            Port 8000            Azure Cloud           Background
   (User)             (Public IP)          (Managed by           (No Port)
                                           Azure)                (Internal)
```

### Step-by-Step Process

| Step | What Happens | Where |
|------|--------------|-------|
| 1 | User types message and clicks "Send" | React Frontend |
| 2 | Frontend sends POST request to API | http://your-aks-ip/api/send |
| 3 | FastAPI receives request | API Pod |
| 4 | API pushes message to Service Bus | Azure Service Bus Queue |
| 5 | Message waits in queue | Azure Cloud |
| 6 | Worker polls queue (every few seconds) | Worker Pod |
| 7 | Worker finds message and processes it | Worker Pod |
| 8 | Worker marks message "complete" | Queue removes message |

### Why Worker Automatically Triggers?

The Worker runs this loop **continuously**:

```python
# This is what worker.py does
while True:
    # Ask Service Bus: "Any new messages?"
    message = queue.receive()  
    
    if message:
        # Process it immediately
        process_message(message)
        queue.complete(message)
    
    # Wait a bit, then check again
    time.sleep(1)
```

**No external trigger needed!** The Worker is always checking for new messages.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        AKS Cluster                       │
│                                                          │
│  ┌──────────────────┐      ┌──────────────────┐         │
│  │   API Pod (2x)   │      │  Worker Pod (2x) │         │
│  │   FastAPI        │      │  Background      │         │
│  │   Receives HTTP  │      │  Processes Queue │         │
│  └────────┬─────────┘      └──────────────────┘         │
│           │                                              │
│           ▼                                              │
│  ┌──────────────────┐                                   │
│  │   Service        │  ←─ Public IP or Ingress          │
│  │   (LoadBalancer) │                                   │
│  └──────────────────┘                                   │
└─────────────────────────────────────────────────────────┘
```

## Why 2 Deployments?

| Component | Purpose | Exposed | Replicas |
|-----------|---------|---------|----------|
| **API** | Receive HTTP from frontend | Yes (LoadBalancer/Ingress) | 2+ |
| **Worker** | Process messages from queue | No | 2+ |

### Why Worker Doesn't Need a Service?

```
API Pod:
  - Needs to receive HTTP requests from internet
  - Needs a Service (LoadBalancer) to expose port 8000
  - Users access it via public IP

Worker Pod:
  - Only connects OUT to Azure Service Bus
  - Doesn't receive any incoming connections
  - No Service needed!
  - Works like a background job
```

## Deploy Steps

### 1. Create Azure Container Registry (ACR)

```bash
# Create ACR
az acr create --resource-group June-RG --name yourRegistryName --sku Basic

# Login to ACR
az acr login --name yourRegistryName
```

### 2. Build and Push Docker Images

```bash
# Build API image
cd backend
docker build -t yourregistryname.azurecr.io/servicebus-api:latest .

# Build Worker image
docker build -f Dockerfile.worker -t yourregistryname.azurecr.io/servicebus-worker:latest .

# Push to ACR
docker push yourregistryname.azurecr.io/servicebus-api:latest
docker push yourregistryname.azurecr.io/servicebus-worker:latest
```

### 3. Create AKS Cluster

```bash
# Create AKS
az aks create \
  --resource-group June-RG \
  --name servicebus-aks \
  --node-count 2 \
  --generate-ssh-keys \
  --attach-acr yourregistryname

# Get credentials
az aks get-credentials --resource-group June-RG --name servicebus-aks
```

### 4. Update Kubernetes Manifests

Edit `k8s/03-api-deployment.yaml` and `k8s/05-worker-deployment.yaml`:
- Replace `your-registry.azurecr.io` with your actual ACR name

Edit `k8s/02-secret.yaml`:
- Replace `YOUR_KEY_HERE` with your actual Service Bus key

### 5. Deploy to AKS

```bash
cd k8s

# Apply all manifests
kubectl apply -f 01-configmap.yaml
kubectl apply -f 02-secret.yaml
kubectl apply -f 03-api-deployment.yaml
kubectl apply -f 04-api-service.yaml
kubectl apply -f 05-worker-deployment.yaml

# Or apply all at once
kubectl apply -f .
```

### 6. Verify Deployment

```bash
# Check pods
kubectl get pods

# Expected output:
# NAME                               READY   STATUS    RESTARTS   AGE
# servicebus-api-xxxxxx-xxxx         1/1     Running   0          1m
# servicebus-api-xxxxxx-yyyy         1/1     Running   0          1m
# servicebus-worker-xxxxxx-xxxx      1/1     Running   0          1m
# servicebus-worker-xxxxxx-yyyy      1/1     Running   0          1m

# Get API public IP
kubectl get service servicebus-api
```

### 7. Update Frontend

Update `frontend/src/App.jsx` with the AKS API URL:

```javascript
const API_URL = 'http://<YOUR-AKS-PUBLIC-IP>'
```

## Scaling

### Manual Scaling
```bash
# Scale API to 3 replicas
kubectl scale deployment servicebus-api --replicas=3

# Scale Worker based on queue depth
kubectl scale deployment servicebus-worker --replicas=5
```

### Auto Scaling (HPA)
```bash
# Create Horizontal Pod Autoscaler
kubectl autoscale deployment servicebus-worker --cpu-percent=70 --min=2 --max=10
```

## Monitoring

```bash
# View API logs
kubectl logs -f deployment/servicebus-api

# View Worker logs
kubectl logs -f deployment/servicebus-worker

# View all pods
kubectl get pods -w
```

## Clean Up

```bash
# Delete all resources
kubectl delete -f .

# Delete AKS cluster (stops billing)
az aks delete --resource-group June-RG --name servicebus-aks
```

## Common Questions

### Q: Can I combine API and Worker in one service?

**A: Yes! Two ways:**

#### Option 1: FastAPI BackgroundTasks (Simple)
```python
@app.post("/api/send")
async def send_message(request: MessageRequest, background_tasks: BackgroundTasks):
    # Process AFTER returning response
    background_tasks.add_task(process_message, request.content)
    return {"success": True}  # User gets immediate response
```

**Pros:**
- Simple, no extra infrastructure
- Good for light processing

**Cons:**
- Only runs when API receives requests
- If pod dies, queued tasks are lost
- Can't scale worker independently

#### Option 2: Background Thread with Service Bus (Better)
```python
@app.on_event("startup")
async def startup_event():
    # Start worker thread when API starts
    worker_thread = threading.Thread(target=run_worker, daemon=True)
    worker_thread.start()
```

**Pros:**
- Continuous polling like separate worker
- One deployment to manage
- Messages survive pod restart (stored in Service Bus)

**Cons:**
- Can't scale API and Worker independently
- Resource contention

#### Comparison Table

| Feature | Separate Deployments | Combined Service |
|---------|---------------------|------------------|
| Scale API independently | ✅ Yes | ❌ No |
| Scale Worker independently | ✅ Yes | ❌ No |
| Simplicity | ❌ 2 deployments | ✅ 1 deployment |
| Resource isolation | ✅ Separate | ❌ Shared |
| **Recommended for** | **Production** | **Simple apps** |

#### When to Use What?

```
Use SEPARATE deployments when:
✅ High traffic (need to scale API vs Worker differently)
✅ Heavy processing (don't want to slow down API)
✅ Production workloads

Use COMBINED service when:
✅ Low traffic
✅ Simple prototype/MVP
✅ Want simpler deployment
```

See `backend/main_combined.py` for the combined code example.

---

### Q: How does Worker know when to process?

**A: Worker continuously polls the queue.** It asks Service Bus "any new messages?" every second. When a message arrives, it's picked up immediately.

No webhook, no trigger, no event needed - just polling.

### Q: Why 2 deployments instead of 1?

**A: Different scaling needs.**

- **API**: Scale based on HTTP requests
- **Worker**: Scale based on queue depth

Example: If 1000 messages in queue but only 10 API requests, scale Worker to 10, keep API at 2.

### Q: Can I use 1 container with both API and Worker?

**A: Yes, but not recommended.**

```
❌ Combined (bad practice):
┌─────────────────────┐
│  One Container      │
│  - API (port 8000)  │
│  - Worker (loop)    │
└─────────────────────┘
Problems:
- Can't scale independently
- API crash affects Worker
- Resource contention

✅ Separated (best practice):
┌─────────────┐  ┌─────────────┐
│  API Pod    │  │ Worker Pod  │
└─────────────┘  └─────────────┘
Benefits:
- Scale independently
- Isolated failures
- Clear separation of concerns
```

### Q: What if Worker crashes?

**A: Kubernetes restarts it automatically.**

If Worker crashes mid-processing:
1. Message is NOT completed
2. Message returns to queue after "lock duration" (default 30 seconds)
3. Another Worker pod picks it up
4. No message loss!

### Q: What if queue has 10,000 messages?

**A: Scale up Worker pods.**

```bash
# Scale to 10 workers
kubectl scale deployment servicebus-worker --replicas=10

# All 10 workers process messages in parallel
# Queue drains faster!
```

Or use HPA (Horizontal Pod Autoscaler) to auto-scale based on CPU or custom metrics.

---

## Production Tips

1. **Use Azure Key Vault** for secrets (not Kubernetes Secrets)
2. **Use Ingress** with TLS instead of LoadBalancer
3. **Add monitoring** (Azure Monitor, Prometheus)
4. **Set resource limits** to prevent runaway pods
5. **Use liveness/readiness probes** for API
6. **Configure autoscaling** based on queue depth

## Files

```
k8s/
├── 01-configmap.yaml      # Non-sensitive config
├── 02-secret.yaml         # Connection string (CHANGE THIS!)
├── 03-api-deployment.yaml # FastAPI pods
├── 04-api-service.yaml    # LoadBalancer for API
└── 05-worker-deployment.yaml  # Worker pods (no service needed)
```
