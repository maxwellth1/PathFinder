# Error Handling & Logging Strategy

## Error Handling Architecture

### Error Types and Categories

```javascript
// Custom Error Classes
class AppError extends Error {
  constructor(message, statusCode, errorCode, isOperational = true) {
    super(message);
    this.statusCode = statusCode;
    this.errorCode = errorCode;
    this.isOperational = isOperational;
    this.timestamp = new Date().toISOString();
    
    Error.captureStackTrace(this, this.constructor);
  }
}

// Specific Error Types
class ValidationError extends AppError {
  constructor(message, details) {
    super(message, 400, 'VALIDATION_ERROR');
    this.details = details;
  }
}

class AuthenticationError extends AppError {
  constructor(message = 'Authentication failed') {
    super(message, 401, 'AUTHENTICATION_ERROR');
  }
}

class AuthorizationError extends AppError {
  constructor(message = 'Access denied') {
    super(message, 403, 'AUTHORIZATION_ERROR');
  }
}

class NotFoundError extends AppError {
  constructor(resource) {
    super(`${resource} not found`, 404, 'NOT_FOUND');
    this.resource = resource;
  }
}

class ConflictError extends AppError {
  constructor(message, conflictingResource) {
    super(message, 409, 'CONFLICT');
    this.conflictingResource = conflictingResource;
  }
}

class RateLimitError extends AppError {
  constructor(retryAfter) {
    super('Too many requests', 429, 'RATE_LIMIT_EXCEEDED');
    this.retryAfter = retryAfter;
  }
}

class ExternalServiceError extends AppError {
  constructor(service, originalError) {
    super(`External service error: ${service}`, 503, 'EXTERNAL_SERVICE_ERROR', false);
    this.service = service;
    this.originalError = originalError;
  }
}
```

### Global Error Handler

```javascript
// Express Error Middleware
const errorHandler = (err, req, res, next) => {
  // Log error
  logger.error({
    error: {
      message: err.message,
      stack: err.stack,
      code: err.errorCode,
      statusCode: err.statusCode
    },
    request: {
      method: req.method,
      url: req.originalUrl,
      ip: req.ip,
      userId: req.user?.id,
      headers: sanitizeHeaders(req.headers)
    },
    timestamp: new Date().toISOString()
  });

  // Send error to monitoring service
  if (!err.isOperational) {
    Sentry.captureException(err, {
      user: { id: req.user?.id },
      extra: {
        requestId: req.id,
        url: req.originalUrl
      }
    });
  }

  // Prepare error response
  const response = {
    error: {
      code: err.errorCode || 'INTERNAL_ERROR',
      message: err.isOperational ? err.message : 'An unexpected error occurred',
      ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
    },
    requestId: req.id,
    timestamp: new Date().toISOString()
  };

  // Add specific error details
  if (err instanceof ValidationError) {
    response.error.details = err.details;
  } else if (err instanceof RateLimitError) {
    response.error.retryAfter = err.retryAfter;
    res.setHeader('Retry-After', err.retryAfter);
  }

  // Send response
  res.status(err.statusCode || 500).json(response);
};

// Async Error Wrapper
const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next);
};
```

### Error Handling in Different Layers

```javascript
// Controller Layer
const messageController = {
  sendMessage: asyncHandler(async (req, res) => {
    const { conversationId, content } = req.body;
    
    // Validation
    if (!content || content.trim().length === 0) {
      throw new ValidationError('Message content is required', {
        field: 'content',
        value: content
      });
    }
    
    // Check authorization
    const hasAccess = await checkConversationAccess(req.user.id, conversationId);
    if (!hasAccess) {
      throw new AuthorizationError('You do not have access to this conversation');
    }
    
    // Business logic
    try {
      const message = await messageService.create({
        conversationId,
        senderId: req.user.id,
        content
      });
      
      res.status(201).json({ message });
    } catch (error) {
      if (error.code === 'CONVERSATION_NOT_FOUND') {
        throw new NotFoundError('Conversation');
      }
      throw error;
    }
  })
};

// Service Layer
class MessageService {
  async create(data) {
    try {
      const message = await db.messages.create(data);
      
      // Publish to queue
      await messageQueue.publish('message.created', {
        messageId: message.id,
        conversationId: message.conversationId
      });
      
      return message;
    } catch (error) {
      // Database errors
      if (error.code === '23505') { // Unique violation
        throw new ConflictError('Message already exists', 'message');
      }
      
      // Queue errors
      if (error.name === 'QueueConnectionError') {
        throw new ExternalServiceError('MessageQueue', error);
      }
      
      throw error;
    }
  }
}
```

## Logging Architecture

### Structured Logging

```javascript
// Winston Logger Configuration
const winston = require('winston');
const { format } = winston;

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: format.combine(
    format.timestamp(),
    format.errors({ stack: true }),
    format.metadata(),
    format.json()
  ),
  defaultMeta: {
    service: 'messaging-api',
    environment: process.env.NODE_ENV,
    version: process.env.APP_VERSION
  },
  transports: [
    // Console transport for development
    new winston.transports.Console({
      format: format.combine(
        format.colorize(),
        format.simple()
      ),
      silent: process.env.NODE_ENV === 'test'
    }),
    
    // File transport for production
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error',
      maxsize: 10485760, // 10MB
      maxFiles: 5
    }),
    
    // File transport for all logs
    new winston.transports.File({
      filename: 'logs/combined.log',
      maxsize: 10485760, // 10MB
      maxFiles: 10
    })
  ]
});

// Add DataDog transport in production
if (process.env.NODE_ENV === 'production') {
  const DatadogTransport = require('winston-datadog-transport');
  logger.add(new DatadogTransport({
    apiKey: process.env.DATADOG_API_KEY,
    hostname: process.env.HOSTNAME,
    service: 'messaging-api',
    ddsource: 'nodejs',
    ddtags: `env:${process.env.NODE_ENV},version:${process.env.APP_VERSION}`
  }));
}
```

### Log Levels and When to Use Them

```javascript
// Log Levels
const LogLevel = {
  ERROR: 'error',     // System errors, exceptions
  WARN: 'warn',       // Warning conditions
  INFO: 'info',       // Informational messages
  HTTP: 'http',       // HTTP requests
  DEBUG: 'debug',     // Debug information
  SILLY: 'silly'      // Very detailed debug info
};

// Usage Examples
logger.error('Database connection failed', {
  error: error.message,
  host: dbConfig.host,
  port: dbConfig.port
});

logger.warn('Rate limit approaching', {
  userId: user.id,
  currentRate: 95,
  limit: 100
});

logger.info('User logged in', {
  userId: user.id,
  method: 'password',
  ip: req.ip
});

logger.http('API request', {
  method: req.method,
  url: req.url,
  responseTime: Date.now() - req.startTime,
  statusCode: res.statusCode
});

logger.debug('Cache miss', {
  key: cacheKey,
  operation: 'getUserPreferences'
});
```

### Request Logging Middleware

```javascript
// Morgan + Winston Integration
const morgan = require('morgan');

// Custom Morgan token for user ID
morgan.token('user-id', (req) => req.user?.id || 'anonymous');

// Custom Morgan token for request ID
morgan.token('request-id', (req) => req.id);

// Morgan format
const morganFormat = ':request-id :user-id :method :url :status :response-time ms';

// Morgan middleware
app.use(morgan(morganFormat, {
  stream: {
    write: (message) => {
      const [requestId, userId, method, url, status, responseTime] = message.trim().split(' ');
      
      logger.http('HTTP Request', {
        requestId,
        userId,
        method,
        url,
        status: parseInt(status),
        responseTime: parseFloat(responseTime),
        timestamp: new Date().toISOString()
      });
    }
  },
  skip: (req) => req.url === '/health' // Skip health checks
}));

// Request context middleware
app.use((req, res, next) => {
  req.id = uuidv4();
  req.startTime = Date.now();
  
  // Log request body for debugging (be careful with sensitive data)
  if (process.env.LOG_REQUEST_BODY === 'true' && req.body) {
    logger.debug('Request body', {
      requestId: req.id,
      body: sanitizeRequestBody(req.body)
    });
  }
  
  next();
});
```

### Performance Logging

```javascript
// Performance monitoring
class PerformanceLogger {
  static async measureAsync(operation, fn, metadata = {}) {
    const start = process.hrtime.bigint();
    const startMemory = process.memoryUsage();
    
    try {
      const result = await fn();
      const end = process.hrtime.bigint();
      const duration = Number(end - start) / 1000000; // Convert to ms
      
      const endMemory = process.memoryUsage();
      const memoryDelta = {
        heapUsed: endMemory.heapUsed - startMemory.heapUsed,
        external: endMemory.external - startMemory.external
      };
      
      logger.info('Operation completed', {
        operation,
        duration,
        memoryDelta,
        ...metadata,
        success: true
      });
      
      // Alert if operation is slow
      if (duration > 1000) {
        logger.warn('Slow operation detected', {
          operation,
          duration,
          threshold: 1000,
          ...metadata
        });
      }
      
      return result;
    } catch (error) {
      const end = process.hrtime.bigint();
      const duration = Number(end - start) / 1000000;
      
      logger.error('Operation failed', {
        operation,
        duration,
        error: error.message,
        ...metadata,
        success: false
      });
      
      throw error;
    }
  }
}

// Usage
const messages = await PerformanceLogger.measureAsync(
  'fetchUserMessages',
  () => messageService.getMessages(userId, { limit: 50 }),
  { userId, limit: 50 }
);
```

### Security Logging

```javascript
// Security event logger
class SecurityLogger {
  static logAuthFailure(req, reason) {
    logger.warn('Authentication failure', {
      event: 'auth_failure',
      reason,
      ip: req.ip,
      userAgent: req.get('user-agent'),
      username: req.body.username,
      timestamp: new Date().toISOString()
    });
  }
  
  static logSuspiciousActivity(req, activity) {
    logger.error('Suspicious activity detected', {
      event: 'suspicious_activity',
      activity,
      ip: req.ip,
      userAgent: req.get('user-agent'),
      userId: req.user?.id,
      url: req.originalUrl,
      timestamp: new Date().toISOString()
    });
    
    // Alert security team
    alertSecurityTeam({
      type: 'suspicious_activity',
      details: { activity, ip: req.ip, url: req.originalUrl }
    });
  }
  
  static logAccessViolation(req, resource) {
    logger.error('Access violation', {
      event: 'access_violation',
      resource,
      userId: req.user?.id,
      ip: req.ip,
      url: req.originalUrl,
      timestamp: new Date().toISOString()
    });
  }
}

// Usage in middleware
app.use('/admin', (req, res, next) => {
  if (!req.user?.isAdmin) {
    SecurityLogger.logAccessViolation(req, 'admin_panel');
    throw new AuthorizationError('Admin access required');
  }
  next();
});
```

### Log Aggregation and Analysis

```javascript
// ELK Stack Integration
const { Client } = require('@elastic/elasticsearch');
const elasticClient = new Client({
  node: process.env.ELASTICSEARCH_URL
});

// Custom Winston transport for Elasticsearch
class ElasticsearchTransport extends winston.Transport {
  async log(info, callback) {
    setImmediate(() => {
      this.emit('logged', info);
    });
    
    try {
      await elasticClient.index({
        index: `logs-${new Date().toISOString().split('T')[0]}`,
        body: {
          ...info,
          '@timestamp': new Date().toISOString(),
          environment: process.env.NODE_ENV,
          hostname: os.hostname()
        }
      });
    } catch (error) {
      console.error('Failed to send log to Elasticsearch:', error);
    }
    
    callback();
  }
}

// Add to logger
if (process.env.ELASTICSEARCH_ENABLED === 'true') {
  logger.add(new ElasticsearchTransport());
}
```

### Log Rotation and Retention

```javascript
// Winston Daily Rotate File
const DailyRotateFile = require('winston-daily-rotate-file');

const fileRotateTransport = new DailyRotateFile({
  filename: 'logs/application-%DATE%.log',
  datePattern: 'YYYY-MM-DD',
  maxSize: '100m',
  maxFiles: '30d',
  compress: true,
  format: format.combine(
    format.timestamp(),
    format.json()
  )
});

logger.add(fileRotateTransport);

// Cleanup old logs
const cleanupOldLogs = async () => {
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
  
  // Delete logs older than 30 days from S3
  await s3.deleteObjects({
    Bucket: 'app-logs',
    Delete: {
      Objects: await getOldLogFiles(thirtyDaysAgo)
    }
  }).promise();
};

// Schedule cleanup
cron.schedule('0 2 * * *', cleanupOldLogs); // Run at 2 AM daily
```

### Debug Logging

```javascript
// Debug namespace
const debug = require('debug');
const dbDebug = debug('app:database');
const cacheDebug = debug('app:cache');
const wsDebug = debug('app:websocket');

// Usage
dbDebug('Executing query: %s', query);
cacheDebug('Cache hit for key: %s', key);
wsDebug('New connection from user: %s', userId);

// Enable with DEBUG environment variable
// DEBUG=app:* node server.js
// DEBUG=app:database,app:cache node server.js
```

### Correlation IDs

```javascript
// Correlation ID middleware
const { v4: uuidv4 } = require('uuid');
const cls = require('cls-hooked');

const namespace = cls.createNamespace('app');

// Middleware to set correlation ID
app.use((req, res, next) => {
  namespace.run(() => {
    const correlationId = req.headers['x-correlation-id'] || uuidv4();
    namespace.set('correlationId', correlationId);
    req.correlationId = correlationId;
    res.setHeader('X-Correlation-ID', correlationId);
    next();
  });
});

// Logger with correlation ID
const logWithCorrelation = (level, message, meta = {}) => {
  const correlationId = namespace.get('correlationId');
  logger[level](message, {
    correlationId,
    ...meta
  });
};

// Usage
logWithCorrelation('info', 'Processing message', {
  messageId: message.id,
  conversationId: message.conversationId
});
```

## Monitoring Dashboard

```javascript
// Health check endpoint
app.get('/health', async (req, res) => {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    checks: {}
  };
  
  // Database health
  try {
    await db.raw('SELECT 1');
    health.checks.database = { status: 'healthy' };
  } catch (error) {
    health.checks.database = { status: 'unhealthy', error: error.message };
    health.status = 'unhealthy';
  }
  
  // Redis health
  try {
    await redis.ping();
    health.checks.redis = { status: 'healthy' };
  } catch (error) {
    health.checks.redis = { status: 'unhealthy', error: error.message };
    health.status = 'unhealthy';
  }
  
  // Message queue health
  try {
    await messageQueue.checkHealth();
    health.checks.messageQueue = { status: 'healthy' };
  } catch (error) {
    health.checks.messageQueue = { status: 'unhealthy', error: error.message };
    health.status = 'unhealthy';
  }
  
  const statusCode = health.status === 'healthy' ? 200 : 503;
  res.status(statusCode).json(health);
});

// Metrics endpoint
app.get('/metrics', (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(register.metrics());
});
```

## Best Practices

1. **Error Handling**
   - Always use custom error classes
   - Distinguish between operational and programming errors
   - Never expose internal errors to clients
   - Log all errors with appropriate context

2. **Logging**
   - Use structured logging (JSON format)
   - Include correlation IDs for request tracing
   - Log at appropriate levels
   - Sanitize sensitive data before logging
   - Implement log rotation and retention policies

3. **Performance**
   - Monitor slow operations
   - Set up alerts for performance degradation
   - Use APM tools for detailed insights
   - Track custom business metrics

4. **Security**
   - Log all authentication attempts
   - Monitor for suspicious patterns
   - Alert on security violations
   - Regular audit log reviews