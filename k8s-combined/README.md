# AKS Deployment - Combined Service (API + Worker in One)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        AKS Cluster                       │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Combined Pod (2x replicas)              │   │
│  │                                                   │   │
│  │   ┌─────────────┐    ┌─────────────┐             │   │
│  │   │  FastAPI    │    │ Background  │             │   │
│  │   │  (Port 8000)│    │ Tasks       │             │   │
│  │   │             │    │ (Same Proc) │             │   │
│  │   └─────────────┘    └─────────────┘             │   │
│  └──────────────────────────────────────────────────┘   │
│                          │                               │
│                          ▼                               │
│                 ┌──────────────────┐                    │
│                 │   Service        │                    │
│                 │   (LoadBalancer) │                    │
│                 └──────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

## Why Combined?

| Feature | Separate | Combined |
|---------|----------|----------|
| Deployments | 2 | **1** ✅ |
| Complexity | Higher | **Lower** ✅ |
| Scale independently | Yes | No |
| Resource usage | More | **Less** ✅ |
| Best for | Production high-traffic | **Simple apps / MVP** ✅ |

## Deploy Steps

### 1. Build and Push Docker Image

```bash
cd backend

# Build combined image
docker build -f Dockerfile.combined -t yourregistry.azurecr.io/servicebus-combined:latest .

# Push to ACR
docker push yourregistry.azurecr.io/servicebus-combined:latest
```

### 2. Update Manifests

Edit `02-secret.yaml`:
```yaml
AZURE_SERVICE_BUS_CONNECTION_STRING: "Endpoint=sb://your-namespace.servicebus.windows.net/;..."
```

Edit `03-deployment.yaml`:
```yaml
image: yourregistry.azurecr.io/servicebus-combined:latest
```

### 3. Deploy to AKS

```bash
# Apply all manifests
kubectl apply -f k8s-combined/

# Check pods
kubectl get pods

# Expected:
# NAME                                    READY   STATUS    RESTARTS   AGE
# servicebus-combined-xxxxxx-xxxx         1/1     Running   0          1m
# servicebus-combined-xxxxxx-yyyy         1/1     Running   0          1m

# Get public IP
kubectl get service servicebus-combined
```

### 4. Test

```bash
# Check status
curl http://<PUBLIC-IP>/api/status

# Send message
curl -X POST http://<PUBLIC-IP>/api/send \
  -H "Content-Type: application/json" \
  -d '{"content": "hello", "priority": "normal"}'
```

## Files

```
k8s-combined/
├── 01-configmap.yaml    # Non-sensitive config
├── 02-secret.yaml       # Connection string (CHANGE THIS!)
├── 03-deployment.yaml   # Combined API + Worker pods
└── 04-service.yaml      # LoadBalancer for public access
```

## Scaling

```bash
# Scale up
kubectl scale deployment servicebus-combined --replicas=5

# Auto-scale
kubectl autoscale deployment servicebus-combined --cpu-percent=70 --min=2 --max=10
```

## Monitoring

```bash
# View logs (shows API + Background tasks)
kubectl logs -f deployment/servicebus-combined

# You'll see:
# INFO: POST /api/send - 200 OK
# ==================================================
# [10:34:49] Background Processing
# Content: hello
# ✅ Done!
# ==================================================
```
