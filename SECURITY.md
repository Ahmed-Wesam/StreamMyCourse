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

## AWS account id in IAM policy JSON (`YOUR_AWS_ACCOUNT_ID`)

The files `infrastructure/iam-policy-github-deploy-*.json` and `infrastructure/iam-trust-github-oidc.json` use the placeholder **`YOUR_AWS_ACCOUNT_ID`** in ARNs. That string is **not** read from GitHub Variables; it is **not** a credential.

**Applying inline policies:** run [`scripts/apply-github-deploy-role-policies.sh`](scripts/apply-github-deploy-role-policies.sh) or [`scripts/apply-github-deploy-role-policies.ps1`](scripts/apply-github-deploy-role-policies.ps1) with admin IAM credentials. Those scripts substitute the placeholder using **`aws sts get-caller-identity`**, then upload the result with **`iam put-role-policy`**.

**CloudFormation:** [`infrastructure/templates/github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml) uses **`!Sub`** / **`${AWS::AccountId}`** instead; no placeholder in the template.

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
