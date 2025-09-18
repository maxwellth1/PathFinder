# Deployment & Infrastructure Setup

## Infrastructure Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                      Production Environment                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐           │
│  │   CloudFlare    │        │   Route 53     │        │   AWS WAF       │           │
│  │   (CDN/DDoS)    │───────►│   (DNS)        │───────►│   (Firewall)    │           │
│  └─────────────────┘        └─────────────────┘        └────────┬────────┘           │
│                                                                  │                      │
│                                    ┌─────────────────────────────┼──────────────┐      │
│                                    │          Application Load Balancer          │      │
│                                    │            (Multi-AZ)                       │      │
│                                    └─────────────────┬───────────────────────────┘      │
│                                                      │                                  │
│         ┌────────────────────────────────────────────┼────────────────────────────┐    │
│         │                                            │                            │    │
│   ┌─────┴─────────┐                          ┌──────┴────────┐            ┌──────┴──┐  │
│   │  ECS Cluster  │                          │  ECS Cluster  │            │   ECS   │  │
│   │   (Zone A)    │                          │   (Zone B)    │            │ (Zone C)│  │
│   │               │                          │               │            │         │  │
│   │ • API Service │                          │ • API Service │            │ • API   │  │
│   │ • WS Service  │                          │ • WS Service  │            │ • WS    │  │
│   │ • Workers     │                          │ • Workers     │            │ • Work  │  │
│   └───────────────┘                          └───────────────┘            └─────────┘  │
│                                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│   │                              Managed Services Layer                              │ │
│   ├─────────────────────────────────────────────────────────────────────────────────┤ │
│   │                                                                                  │ │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │ │
│   │  │   RDS        │  │   ElastiCache│  │   Amazon MQ  │  │   S3         │      │ │
│   │  │ PostgreSQL   │  │   (Redis)    │  │  (RabbitMQ)  │  │  Storage     │      │ │
│   │  │  Multi-AZ    │  │   Cluster    │  │   Cluster    │  │              │      │ │
│   │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘      │ │
│   │                                                                                  │ │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │ │
│   │  │ Elasticsearch│  │   Secrets    │  │   Parameter  │  │   CloudWatch │      │ │
│   │  │   Service    │  │   Manager    │  │    Store     │  │   Logs       │      │ │
│   │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘      │ │
│   └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

## Docker Configuration

### API Service Dockerfile

```dockerfile
# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile --production=false

# Copy source code
COPY . .

# Build TypeScript
RUN yarn build

# Prune dev dependencies
RUN yarn install --frozen-lockfile --production=true

# Runtime stage
FROM node:18-alpine

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Create app user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

WORKDIR /app

# Copy built application
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nodejs:nodejs /app/package.json ./

# Switch to non-root user
USER nodejs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD node healthcheck.js

# Start application with dumb-init
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "dist/server.js"]
```

### Docker Compose for Development

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: messaging_db
      POSTGRES_USER: messaging_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U messaging_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  rabbitmq:
    image: rabbitmq:3-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_running"]
      interval: 10s
      timeout: 5s
      retries: 5

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    environment:
      NODE_ENV: development
      DATABASE_URL: postgresql://messaging_user:${DB_PASSWORD}@postgres:5432/messaging_db
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
      RABBITMQ_URL: amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@rabbitmq:5672
      ELASTICSEARCH_URL: http://elasticsearch:9200
    volumes:
      - ./src:/app/src
      - ./logs:/app/logs
    ports:
      - "3000:3000"
      - "9229:9229" # Debug port
    command: yarn dev

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    depends_on:
      - api
    environment:
      NODE_ENV: development
      DATABASE_URL: postgresql://messaging_user:${DB_PASSWORD}@postgres:5432/messaging_db
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
      RABBITMQ_URL: amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@rabbitmq:5672
    volumes:
      - ./src:/app/src
      - ./logs:/app/logs
    command: yarn worker

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
  elasticsearch_data:
```

## Kubernetes Configuration

### API Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: messaging-api
  namespace: production
  labels:
    app: messaging-api
    tier: backend
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: messaging-api
  template:
    metadata:
      labels:
        app: messaging-api
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - messaging-api
              topologyKey: kubernetes.io/hostname
      containers:
      - name: api
        image: messaging-app/api:latest
        ports:
        - containerPort: 3000
          name: http
        env:
        - name: NODE_ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: messaging-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: messaging-secrets
              key: redis-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 15"]
---
apiVersion: v1
kind: Service
metadata:
  name: messaging-api
  namespace: production
spec:
  selector:
    app: messaging-api
  ports:
  - port: 80
    targetPort: 3000
    protocol: TCP
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: messaging-api-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: messaging-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### WebSocket Service Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: messaging-websocket
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: messaging-websocket
  template:
    metadata:
      labels:
        app: messaging-websocket
    spec:
      containers:
      - name: websocket
        image: messaging-app/websocket:latest
        ports:
        - containerPort: 3001
          name: ws
        env:
        - name: STICKY_SESSIONS
          value: "true"
        - name: REDIS_ADAPTER
          value: "true"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: messaging-websocket
  namespace: production
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"
spec:
  type: LoadBalancer
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 86400
  selector:
    app: messaging-websocket
  ports:
  - port: 80
    targetPort: 3001
    protocol: TCP
```

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'yarn'
    
    - name: Install dependencies
      run: yarn install --frozen-lockfile
    
    - name: Run linter
      run: yarn lint
    
    - name: Run type checking
      run: yarn type-check
    
    - name: Run tests
      run: yarn test:ci
      env:
        DATABASE_URL: postgresql://postgres:testpass@localhost:5432/test
        REDIS_URL: redis://localhost:6379
    
    - name: Generate coverage report
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage/lcov.info

  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=sha,prefix={{branch}}-
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy-staging:
    needs: build
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: staging
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Deploy to ECS
      run: |
        aws ecs update-service \
          --cluster messaging-staging \
          --service messaging-api \
          --force-new-deployment

  deploy-production:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Deploy to ECS
      run: |
        # Update task definition
        aws ecs register-task-definition \
          --cli-input-json file://ecs/task-definition-prod.json
        
        # Update service with new task definition
        aws ecs update-service \
          --cluster messaging-production \
          --service messaging-api \
          --task-definition messaging-api:latest \
          --desired-count 3
    
    - name: Wait for deployment
      run: |
        aws ecs wait services-stable \
          --cluster messaging-production \
          --services messaging-api
```

## Infrastructure as Code (Terraform)

### Main Infrastructure

```hcl
# main.tf
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "messaging-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
    encrypt = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC Configuration
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"
  
  name = "${var.project_name}-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = true
  enable_dns_hostnames = true
  
  tags = var.common_tags
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = var.common_tags
}

# RDS PostgreSQL
module "rds" {
  source = "terraform-aws-modules/rds/aws"
  version = "6.0.0"
  
  identifier = "${var.project_name}-db"
  
  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = "db.r6g.large"
  allocated_storage = 100
  storage_encrypted = true
  
  db_name  = "messaging"
  username = "dbadmin"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  
  multi_az               = true
  subnet_ids             = module.vpc.database_subnets
  create_db_subnet_group = true
  
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  enabled_cloudwatch_logs_exports = ["postgresql"]
  
  tags = var.common_tags
}

# ElastiCache Redis Cluster
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${var.project_name}-redis"
  replication_group_description = "Redis cluster for messaging app"
  
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = "cache.r6g.large"
  number_cache_clusters = 3
  
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  subnet_group_name = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token = var.redis_auth_token
  
  snapshot_retention_limit = 7
  snapshot_window         = "03:00-05:00"
  
  tags = var.common_tags
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnets
  
  enable_deletion_protection = true
  enable_http2              = true
  
  tags = var.common_tags
}

# Auto Scaling
resource "aws_appautoscaling_target" "ecs_target" {
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = 3
  max_capacity       = 20
}

resource "aws_appautoscaling_policy" "ecs_policy_cpu" {
  name               = "${var.project_name}-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
```

## Monitoring and Observability

### CloudWatch Dashboards

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ECS", "CPUUtilization", "ServiceName", "messaging-api"],
          [".", "MemoryUtilization", ".", "."]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "ECS Service Metrics"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "messaging-alb"],
          [".", "RequestCount", ".", ".", { "stat": "Sum" }],
          [".", "HTTPCode_Target_5XX_Count", ".", ".", { "stat": "Sum" }]
        ],
        "period": 60,
        "stat": "Average",
        "region": "us-east-1",
        "title": "ALB Metrics"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "messaging-db"],
          [".", "DatabaseConnections", ".", "."],
          [".", "FreeableMemory", ".", "."]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "RDS Metrics"
      }
    }
  ]
}
```

### Alerting Configuration

```yaml
# CloudWatch Alarms
alarms:
  - name: high-cpu-usage
    metric: CPUUtilization
    threshold: 80
    evaluationPeriods: 2
    actions:
      - sns:alert-topic
      - auto-scaling:scale-up

  - name: high-error-rate
    metric: HTTPCode_5XX_Count
    threshold: 10
    evaluationPeriods: 1
    actions:
      - sns:critical-alerts
      - pagerduty:trigger

  - name: database-connection-limit
    metric: DatabaseConnections
    threshold: 80
    evaluationPeriods: 2
    actions:
      - sns:database-alerts
      - slack:notify-dba

  - name: low-disk-space
    metric: FreeStorageSpace
    threshold: 10737418240  # 10GB
    evaluationPeriods: 1
    actions:
      - sns:critical-alerts
      - auto-scaling:increase-storage
```

## Security Configuration

### AWS Security Groups

```hcl
# ALB Security Group
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-alb-"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-alb-sg"
  })
}

# Application Security Group
resource "aws_security_group" "app" {
  name_prefix = "${var.project_name}-app-"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(var.common_tags, {
    Name = "${var.project_name}-app-sg"
  })
}
```

### Secrets Management

```bash
# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name messaging-app/production \
  --secret-string '{
    "database_url": "postgresql://...",
    "redis_url": "rediss://...",
    "jwt_secret": "...",
    "sendgrid_api_key": "...",
    "aws_access_key": "...",
    "aws_secret_key": "..."
  }'

# Reference in ECS task definition
"secrets": [
  {
    "name": "DATABASE_URL",
    "valueFrom": "arn:aws:secretsmanager:region:account:secret:messaging-app/production:database_url::"
  }
]
```

## Backup and Disaster Recovery

### Backup Strategy

```yaml
backups:
  database:
    - type: automated
      retention: 30 days
      frequency: daily
      time: "03:00 UTC"
    
    - type: manual
      retention: 90 days
      frequency: weekly
      storage: S3 cross-region
  
  redis:
    - type: snapshot
      retention: 7 days
      frequency: daily
  
  s3:
    - type: replication
      destination: s3://backup-bucket-dr
      storage_class: GLACIER
  
  application:
    - type: ami
      retention: 14 days
      frequency: weekly
```

### Disaster Recovery Plan

1. **RTO (Recovery Time Objective)**: 2 hours
2. **RPO (Recovery Point Objective)**: 1 hour

```bash
# DR Runbook
1. Activate DR environment in secondary region
2. Restore database from latest snapshot
3. Update DNS to point to DR load balancer
4. Verify application functionality
5. Notify stakeholders
```

## Cost Optimization

### Resource Tagging Strategy

```hcl
variable "common_tags" {
  default = {
    Project     = "messaging-app"
    Environment = "production"
    ManagedBy   = "terraform"
    CostCenter  = "engineering"
  }
}
```

### Cost Monitoring

```bash
# Set up AWS Budget alerts
aws budgets create-budget \
  --account-id 123456789012 \
  --budget '{
    "BudgetName": "messaging-app-monthly",
    "BudgetLimit": {
      "Amount": "5000",
      "Unit": "USD"
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }'
```

## Performance Optimization

### CDN Configuration

```javascript
// CloudFront behaviors
const behaviors = {
  '/api/*': {
    cache: false,
    origin: 'alb'
  },
  '/ws/*': {
    cache: false,
    origin: 'websocket-nlb'
  },
  '/static/*': {
    cache: true,
    ttl: 86400,
    origin: 's3'
  },
  '/avatars/*': {
    cache: true,
    ttl: 604800,
    origin: 's3'
  }
};
```

### Database Optimization

```sql
-- Create appropriate indexes
CREATE INDEX idx_messages_conversation_created 
ON messages(conversation_id, created_at DESC);

CREATE INDEX idx_user_conversations_user_last_read 
ON user_conversations(user_id, last_read_at);

-- Enable query performance insights
ALTER DATABASE messaging SET log_statement = 'all';
ALTER DATABASE messaging SET log_duration = on;
```

## Maintenance Windows

```yaml
maintenance:
  database:
    window: "sun:04:00-sun:05:00 UTC"
    notifications:
      - email: ops@company.com
      - slack: #database-maintenance
  
  application:
    deployment_freeze:
      - start: "2023-12-22"
        end: "2024-01-02"
        reason: "Holiday freeze"
    
    scheduled_updates:
      - component: "dependencies"
        frequency: "monthly"
        day: "first Tuesday"
```