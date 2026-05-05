# StreamMyCourse

> A modern video course platform where instructors publish content and students learn anywhere.

[![CI](https://github.com/Ahmed-Wesam/StreamMyCourse/actions/workflows/ci.yml/badge.svg)](https://github.com/Ahmed-Wesam/StreamMyCourse/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Proprietary-blue.svg)](./LICENSE.txt)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?logo=typescript)](https://www.typescriptlang.org)
[![AWS](https://img.shields.io/badge/AWS-Serverless-FF9900?logo=amazon-aws)](https://aws.amazon.com)

## What is StreamMyCourse?

StreamMyCourse is a serverless learning management system (LMS) built for video-first education. Instructors create courses, upload video lessons, and publish content for students to stream on any device.

### For Students

- **Browse courses** - Discover published courses in a clean catalog
- **Stream HD video** - Watch lessons with adaptive streaming via CloudFront CDN
- **One-click enrollment** - Sign in with Google and start learning immediately
- **Responsive design** - Works seamlessly on desktop, tablet, and mobile

### For Instructors

- **Course management** - Create courses with draft/publish workflow
- **Video uploads** - Direct browser-to-S3 uploads with presigned URLs
- **Lesson organization** - Arrange lessons with intuitive ordering
- **Student insights** - Track enrollments and course engagement

## Architecture

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        S[Student SPA<br/>React + Vite + TS]
        T[Teacher SPA<br/>React + Vite + TS]
    end

    subgraph Edge["Edge Layer (CloudFront)"]
        CF_WEB["Static Site CDN<br/>S3 + OAC"]
        CF_VIDEO["Video CDN<br/>S3 + OAC"]
    end

    subgraph Auth["Authentication (Cognito)"]
        CG["User Pool + Google IdP"]
        UPS["PostAuth Lambda<br/>User Profile Sync"]
    end

    subgraph API["API Layer"]
        APIGW["API Gateway<br/>REST API"]
        LAMBDA["Catalog Lambda<br/>Python 3.11"]
    end

    subgraph Storage["Storage Layer"]
        RDS[("RDS PostgreSQL<br/>Courses / Lessons<br/>Enrollments / Users")]
        S3_VIDEO["S3 Video Bucket<br/>Private + Presigned URLs"]
        S3_WEB["S3 Web Bucket<br/>Static Assets"]
    end

    subgraph Async["Async Processing"]
        SQS["Media Cleanup Queue<br/>SQS + DLQ"]
        CLEANUP["Cleanup Worker<br/>Lambda"]
    end

    S -->|"Browse / Watch"| CF_WEB
    T -->|"Create / Manage"| CF_WEB
    CF_WEB --> S3_WEB

    S -->|"Google OAuth"| CG
    T -->|"Google OAuth"| CG
    CG -->|"Sync User"| UPS
    UPS -.->|"Upsert"| RDS

    S -->|"REST API + JWT"| APIGW
    T -->|"REST API + JWT"| APIGW
    APIGW --> LAMBDA

    LAMBDA -->|"Read / Write"| RDS
    LAMBDA -->|"Presigned URLs"| S3_VIDEO
    LAMBDA -->|"Enqueue Delete"| SQS

    S -->|"Stream MP4"| CF_VIDEO
    T -->|"Upload / Stream"| CF_VIDEO
    CF_VIDEO --> S3_VIDEO

    SQS --> CLEANUP
    CLEANUP -->|"DeleteObjects"| S3_VIDEO
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS |
| **Authentication** | AWS Cognito with Google OAuth 2.0 |
| **Backend** | Python 3.11 Lambda, API Gateway |
| **Database** | PostgreSQL (RDS) - production catalog store |
| **Storage** | S3 for video content with CloudFront CDN |
| **Infrastructure** | CloudFormation (IaC), GitHub Actions CI/CD |
| **Testing** | Vitest (frontend), pytest (backend) |

## Quick Start

### Prerequisites

- [Node.js](https://nodejs.org/) 20+
- [Python](https://python.org/) 3.11+
- [AWS CLI](https://aws.amazon.com/cli/) v2 with configured credentials
- [GitHub CLI](https://cli.github.com/) (optional, for secret management)

### Installation

```bash
# Clone the repository
git clone https://github.com/Ahmed-Wesam/StreamMyCourse.git
cd StreamMyCourse

# Install frontend dependencies
cd frontend
npm ci

# Install Python test dependencies (for Lambda development)
pip install -r tests/unit/requirements.txt
```

### Local Development

```bash
# Start student site (port 5173)
npm run dev

# Start teacher site (port 5174)
npm run dev:teacher

# Run tests
npm run test                    # Frontend unit tests
python -m pytest tests/unit     # Lambda unit tests
```

### Environment Setup

Create `frontend/.env` from the example:

```bash
cp frontend/.env.example frontend/.env
```

Configure your API endpoint and Cognito settings (see [frontend/.env.example](frontend/.env.example) for details).

## Deployment

StreamMyCourse deploys to AWS using GitHub Actions with OIDC authentication. Infrastructure is managed via CloudFormation templates.

### Required GitHub Secrets/Variables

| Secret/Variable | Description |
|-----------------|-------------|
| `AWS_DEPLOY_ROLE_ARN` | OIDC role ARN for AWS deployment |
| `AWS_ACCOUNT_ID` | AWS account ID (set on both dev and prod environments) |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth client ID (for auth stack) |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth client secret (for auth stack) |

### Setting AWS Account ID

```bash
# Get your AWS account ID
aws sts get-caller-identity --query Account --output text

# Set as GitHub Actions variable (recommended - per environment)
gh variable set AWS_ACCOUNT_ID --env dev --body "YOUR_ACCOUNT_ID"
gh variable set AWS_ACCOUNT_ID --env prod --body "YOUR_ACCOUNT_ID"
```

See [infrastructure/README.md](infrastructure/README.md) for detailed deployment instructions.

## Documentation

- **[MVP Design & APIs](design.md)** - Architecture decisions, API contracts, and data model
- **[Roadmap](roadmap.md)** - Phase 2 vision: monetization, DRM, and scale
- **[Implementation History](ImplementationHistory.md)** - Engineering decisions and milestones
- **[Developer Guide](AGENTS.md)** - Contribution guidelines and CI/CD details
- **[Infrastructure Guide](infrastructure/README.md)** - AWS setup and deployment

## Project Structure

```
StreamMyCourse/
├── frontend/                    # Vite + React application
│   ├── src/
│   │   ├── student-app/        # Student SPA entry
│   │   ├── teacher-app/        # Teacher SPA entry
│   │   ├── components/         # Reusable UI components
│   │   ├── pages/              # Route-level screens
│   │   └── lib/                # API client, auth, utilities
│   └── package.json
├── infrastructure/
│   ├── lambda/catalog/         # Python Lambda API
│   │   └── services/           # Controller → Service → Repo layers
│   ├── templates/              # CloudFormation stacks
│   └── deploy.ps1              # Deployment script
├── scripts/                    # CI/CD and utility scripts
└── tests/
    ├── unit/                   # Lambda unit tests
    └── integration/            # Integration tests
```

## Security

This repository is proprietary software. For security concerns or vulnerability reports, please contact the maintainers directly.

See [LICENSE.txt](LICENSE.txt) for full terms.

## License

Proprietary and confidential — all rights reserved.  
Copyright (c) 2026 StreamMyCourse. All rights reserved.

---

*Built with modern web technologies on AWS serverless infrastructure.*
