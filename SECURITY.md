# Security Policy

This document outlines the security policy for the StreamMyCourse repository.

## Supported Versions

| Version | Supported |
|---------|-----------|
| main    | Yes       |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow the responsible disclosure process below.

### How to Report

**Please do NOT open a public issue** for security vulnerabilities.

Instead, contact the maintainers directly:

- Email: [security@streammycourse.com] (or appropriate contact method)
- Include a detailed description of the vulnerability
- Include steps to reproduce (if applicable)
- Include potential impact assessment
- Allow reasonable time for response and remediation

### What to Expect

1. **Acknowledgment** - We will acknowledge receipt of your report within 48 hours
2. **Assessment** - We will assess the vulnerability and determine its severity
3. **Remediation** - We will work on a fix and coordinate disclosure timeline
4. **Recognition** - With your permission, we will credit you in our security advisories

## Security Measures

This repository implements the following security practices:

### Infrastructure
- OIDC-based AWS authentication (no long-lived credentials)
- IAM policies with least-privilege access
- CloudFormation for infrastructure as code
- VPC-isolated RDS PostgreSQL databases
- S3 bucket policies with block public access
- CloudFront with Origin Access Control (OAC)

### Authentication & Authorization
- AWS Cognito with Google OAuth 2.0
- JWT-based session management
- Role-based access control (student/teacher/admin)

### Data Protection
- Presigned S3 URLs for video access (time-limited)
- PostgreSQL with encryption at rest
- Secrets Manager for credential storage

### CI/CD Security
- GitHub Actions with OIDC to AWS
- Required reviews before merging
- Automated security scanning (Vulture, ESLint)
- No secrets in repository (all via GitHub Secrets/Variables)

## AWS Account ID Placeholders

The IAM policy JSON files in this repository contain `YOUR_AWS_ACCOUNT_ID` placeholders that must be replaced with your actual AWS account ID before deployment.

### Files Requiring Substitution

- `infrastructure/iam-policy-github-deploy-web.json`
- `infrastructure/iam-policy-github-deploy-backend.json`
- `infrastructure/iam-trust-github-oidc.json`

### How to Set Your AWS Account ID

Set the `AWS_ACCOUNT_ID` as a GitHub Actions variable:

```bash
# Get your AWS account ID
aws sts get-caller-identity --query Account --output text

# Set on dev environment
gh variable set AWS_ACCOUNT_ID --env dev --body "YOUR_ACCOUNT_ID"

# Set on prod environment
gh variable set AWS_ACCOUNT_ID --env prod --body "YOUR_ACCOUNT_ID"
```

## Security Best Practices for Operators

1. **Never commit AWS credentials** to the repository
2. **Rotate secrets regularly** (GitHub tokens, AWS keys)
3. **Enable CloudTrail** for AWS account auditing
4. **Monitor CloudWatch logs** for suspicious activity
5. **Keep dependencies updated** via Dependabot or similar
6. **Review IAM policies** periodically for least-privilege compliance

## License & Proprietary Notice

This is proprietary software. See [LICENSE.txt](LICENSE.txt) for full terms.

Copyright (c) 2026 StreamMyCourse. All rights reserved.
