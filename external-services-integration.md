# External Services Integration

## Overview
This document details all external services integrated into the messaging application backend, including configuration, usage, and best practices.

## 1. AWS Services

### AWS S3 (File Storage)
```javascript
// Configuration
const AWS = require('aws-sdk');
const s3 = new AWS.S3({
  accessKeyId: process.env.AWS_ACCESS_KEY_ID,
  secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  region: process.env.AWS_REGION
});

// Bucket Structure
messaging-app-prod/
├── avatars/
│   └── {userId}/
│       └── {timestamp}-{filename}
├── attachments/
│   └── {conversationId}/
│       └── {messageId}/
│           └── {timestamp}-{filename}
├── thumbnails/
│   └── {messageId}/
│       └── thumb-{size}-{filename}
└── temp/
    └── {uploadId}/
```

**Features:**
- Presigned URLs for secure uploads
- Automatic expiration for temporary files
- CloudFront CDN integration
- S3 Transfer Acceleration for large files
- Lifecycle policies for cost optimization

### AWS CloudFront (CDN)
```yaml
Distribution Settings:
  Origins:
    - S3 Bucket: messaging-app-prod
  Behaviors:
    - Path Pattern: /avatars/*
      Cache: 1 year
    - Path Pattern: /attachments/*
      Cache: 1 week
    - Path Pattern: /thumbnails/*
      Cache: 1 month
  Security:
    - Signed URLs for private content
    - Origin Access Identity (OAI)
```

### AWS Lambda (Image Processing)
```javascript
// Triggered on S3 upload
exports.handler = async (event) => {
  const bucket = event.Records[0].s3.bucket.name;
  const key = event.Records[0].s3.object.key;
  
  // Generate thumbnails
  const sizes = [64, 128, 256, 512];
  for (const size of sizes) {
    await generateThumbnail(bucket, key, size);
  }
  
  // Compress images
  await compressImage(bucket, key);
  
  // Extract metadata
  await extractAndStoreMetadata(bucket, key);
};
```

## 2. Email Services

### SendGrid
```javascript
// Configuration
const sgMail = require('@sendgrid/mail');
sgMail.setApiKey(process.env.SENDGRID_API_KEY);

// Email Templates
const templates = {
  welcome: 'd-xxxxxxxxxxxxx',
  passwordReset: 'd-xxxxxxxxxxxxx',
  newMessage: 'd-xxxxxxxxxxxxx',
  weeklyDigest: 'd-xxxxxxxxxxxxx'
};

// Usage Example
async function sendWelcomeEmail(user) {
  const msg = {
    to: user.email,
    from: 'noreply@messaging-app.com',
    templateId: templates.welcome,
    dynamicTemplateData: {
      name: user.fullName,
      username: user.username,
      verificationUrl: `${BASE_URL}/verify/${user.verificationToken}`
    }
  };
  
  await sgMail.send(msg);
}
```

**Features:**
- Transactional emails
- Email templates with dynamic content
- Bounce and complaint handling
- Analytics and tracking
- Unsubscribe management

## 3. SMS Services (Optional)

### Twilio
```javascript
// Configuration
const twilio = require('twilio');
const client = twilio(
  process.env.TWILIO_ACCOUNT_SID,
  process.env.TWILIO_AUTH_TOKEN
);

// SMS Notifications
async function sendSMSNotification(phoneNumber, message) {
  try {
    const result = await client.messages.create({
      body: message,
      from: process.env.TWILIO_PHONE_NUMBER,
      to: phoneNumber
    });
    return result.sid;
  } catch (error) {
    console.error('SMS send failed:', error);
  }
}

// Phone Verification
async function sendVerificationCode(phoneNumber) {
  const code = generateRandomCode(6);
  await storeVerificationCode(phoneNumber, code);
  
  await sendSMSNotification(
    phoneNumber,
    `Your verification code is: ${code}`
  );
}
```

## 4. Push Notification Services

### Firebase Cloud Messaging (FCM)
```javascript
// Configuration
const admin = require('firebase-admin');
admin.initializeApp({
  credential: admin.credential.cert({
    projectId: process.env.FIREBASE_PROJECT_ID,
    clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
    privateKey: process.env.FIREBASE_PRIVATE_KEY
  })
});

// Send Push Notification
async function sendPushNotification(tokens, notification) {
  const message = {
    notification: {
      title: notification.title,
      body: notification.body
    },
    data: notification.data,
    tokens: tokens,
    android: {
      priority: 'high',
      notification: {
        sound: 'default',
        clickAction: 'OPEN_CONVERSATION'
      }
    },
    apns: {
      payload: {
        aps: {
          sound: 'default',
          badge: notification.badge
        }
      }
    }
  };
  
  const response = await admin.messaging().sendMulticast(message);
  
  // Handle failed tokens
  if (response.failureCount > 0) {
    await handleFailedTokens(tokens, response.responses);
  }
}
```

## 5. Authentication Providers

### Google OAuth 2.0
```javascript
// Configuration
const { OAuth2Client } = require('google-auth-library');
const client = new OAuth2Client(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  `${BASE_URL}/auth/google/callback`
);

// Verify ID Token
async function verifyGoogleToken(idToken) {
  const ticket = await client.verifyIdToken({
    idToken: idToken,
    audience: process.env.GOOGLE_CLIENT_ID
  });
  
  const payload = ticket.getPayload();
  return {
    googleId: payload['sub'],
    email: payload['email'],
    name: payload['name'],
    picture: payload['picture'],
    emailVerified: payload['email_verified']
  };
}
```

### GitHub OAuth
```javascript
// Configuration
const GITHUB_AUTH_URL = 'https://github.com/login/oauth/authorize';
const GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token';
const GITHUB_USER_URL = 'https://api.github.com/user';

// OAuth Flow
router.get('/auth/github', (req, res) => {
  const params = new URLSearchParams({
    client_id: process.env.GITHUB_CLIENT_ID,
    redirect_uri: `${BASE_URL}/auth/github/callback`,
    scope: 'user:email',
    state: generateStateToken()
  });
  
  res.redirect(`${GITHUB_AUTH_URL}?${params}`);
});

router.get('/auth/github/callback', async (req, res) => {
  const { code, state } = req.query;
  
  // Verify state token
  if (!verifyStateToken(state)) {
    return res.status(400).json({ error: 'Invalid state' });
  }
  
  // Exchange code for token
  const tokenResponse = await exchangeCodeForToken(code);
  const userInfo = await fetchGitHubUserInfo(tokenResponse.access_token);
  
  // Create or update user
  const user = await findOrCreateUser({
    githubId: userInfo.id,
    email: userInfo.email,
    username: userInfo.login,
    avatar: userInfo.avatar_url
  });
  
  // Generate JWT and redirect
  const jwt = generateJWT(user);
  res.redirect(`${FRONTEND_URL}/auth/success?token=${jwt}`);
});
```

## 6. Monitoring & Analytics

### DataDog
```javascript
// Configuration
const StatsD = require('node-dogstatsd').StatsD;
const dogstatsd = new StatsD();

// Metrics
dogstatsd.increment('api.requests', 1, ['endpoint:messages', 'method:POST']);
dogstatsd.histogram('api.response_time', responseTime, ['endpoint:messages']);
dogstatsd.gauge('websocket.connections', activeConnections);

// Custom Metrics
function trackMessageSent(conversationType) {
  dogstatsd.increment('messages.sent', 1, [`type:${conversationType}`]);
}

function trackUserActivity(userId, action) {
  dogstatsd.increment('user.activity', 1, [
    `user:${userId}`,
    `action:${action}`
  ]);
}

// APM Integration
const tracer = require('dd-trace').init({
  service: 'messaging-api',
  env: process.env.NODE_ENV,
  version: process.env.APP_VERSION
});
```

### Sentry (Error Tracking)
```javascript
// Configuration
const Sentry = require('@sentry/node');
Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NODE_ENV,
  integrations: [
    new Sentry.Integrations.Http({ tracing: true }),
    new Sentry.Integrations.Express({ app }),
  ],
  tracesSampleRate: 0.1,
  beforeSend(event, hint) {
    // Filter sensitive data
    if (event.request) {
      delete event.request.cookies;
      delete event.request.headers.authorization;
    }
    return event;
  }
});

// Error Handling
app.use(Sentry.Handlers.errorHandler());

// Custom Error Tracking
function logError(error, context) {
  Sentry.withScope((scope) => {
    scope.setContext('custom', context);
    Sentry.captureException(error);
  });
}
```

## 7. Search & Analytics

### Elasticsearch
```javascript
// Configuration
const { Client } = require('@elastic/elasticsearch');
const client = new Client({
  node: process.env.ELASTICSEARCH_URL,
  auth: {
    username: process.env.ELASTICSEARCH_USERNAME,
    password: process.env.ELASTICSEARCH_PASSWORD
  }
});

// Message Indexing
async function indexMessage(message) {
  await client.index({
    index: 'messages',
    id: message.id,
    body: {
      conversationId: message.conversationId,
      senderId: message.senderId,
      content: message.content,
      timestamp: message.createdAt,
      attachments: message.attachments
    }
  });
}

// Search Messages
async function searchMessages(userId, query, options = {}) {
  const { from = 0, size = 20 } = options;
  
  const response = await client.search({
    index: 'messages',
    body: {
      query: {
        bool: {
          must: [
            { match: { content: query } }
          ],
          filter: [
            {
              terms: {
                conversationId: await getUserConversations(userId)
              }
            }
          ]
        }
      },
      from,
      size,
      sort: [{ timestamp: { order: 'desc' } }],
      highlight: {
        fields: {
          content: {}
        }
      }
    }
  });
  
  return response.body.hits;
}
```

## 8. Payment Processing (Future)

### Stripe
```javascript
// Configuration
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

// Subscription Management
async function createSubscription(userId, priceId) {
  // Get or create customer
  const customer = await getOrCreateStripeCustomer(userId);
  
  // Create subscription
  const subscription = await stripe.subscriptions.create({
    customer: customer.id,
    items: [{ price: priceId }],
    payment_behavior: 'default_incomplete',
    expand: ['latest_invoice.payment_intent']
  });
  
  return {
    subscriptionId: subscription.id,
    clientSecret: subscription.latest_invoice.payment_intent.client_secret
  };
}

// Webhook Handler
router.post('/webhooks/stripe', async (req, res) => {
  const sig = req.headers['stripe-signature'];
  
  try {
    const event = stripe.webhooks.constructEvent(
      req.rawBody,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
    
    switch (event.type) {
      case 'payment_intent.succeeded':
        await handlePaymentSuccess(event.data.object);
        break;
      case 'subscription.deleted':
        await handleSubscriptionCancelled(event.data.object);
        break;
    }
    
    res.json({ received: true });
  } catch (err) {
    res.status(400).send(`Webhook Error: ${err.message}`);
  }
});
```

## Environment Variables

```bash
# AWS
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_REGION=us-east-1
AWS_S3_BUCKET=messaging-app-prod

# SendGrid
SENDGRID_API_KEY=xxx

# Twilio
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+1234567890

# Firebase
FIREBASE_PROJECT_ID=xxx
FIREBASE_CLIENT_EMAIL=xxx
FIREBASE_PRIVATE_KEY=xxx

# OAuth
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx

# Monitoring
DATADOG_API_KEY=xxx
SENTRY_DSN=xxx
ELASTICSEARCH_URL=xxx
ELASTICSEARCH_USERNAME=xxx
ELASTICSEARCH_PASSWORD=xxx

# Stripe
STRIPE_SECRET_KEY=xxx
STRIPE_WEBHOOK_SECRET=xxx
```

## Rate Limits & Quotas

| Service | Limit | Notes |
|---------|-------|-------|
| SendGrid | 100k emails/month | Upgrade for higher volume |
| Twilio | Pay per SMS | ~$0.0075 per SMS |
| FCM | Unlimited | Free tier sufficient |
| AWS S3 | Pay per GB | ~$0.023 per GB/month |
| CloudFront | Pay per GB | ~$0.085 per GB transfer |
| Elasticsearch | 2 nodes | Upgrade for production |
| DataDog | 5 hosts | Upgrade based on usage |

## Security Best Practices

1. **API Keys Management**
   - Store all keys in environment variables
   - Rotate keys regularly
   - Use different keys for different environments
   - Implement key encryption at rest

2. **Service Authentication**
   - Use IAM roles for AWS services
   - Implement IP whitelisting where possible
   - Use webhook signatures for verification
   - Enable 2FA for service accounts

3. **Data Privacy**
   - Encrypt sensitive data before storing
   - Implement data retention policies
   - Comply with GDPR/CCPA requirements
   - Regular security audits

4. **Error Handling**
   - Never expose service errors to clients
   - Log errors with appropriate context
   - Implement circuit breakers
   - Have fallback mechanisms