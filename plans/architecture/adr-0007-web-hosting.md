# ADR 0007: Frontend Hosting Architecture

**Status:** Accepted

**Date:** 2026-05-02

**Context:**

The MVP requires hosting the React SPA on a public URL with HTTPS. The solution must:
- Support custom domains for brand recognition
- Handle SPA client-side routing (deep links)
- Be cost-effective (AWS Free Tier where possible)
- Work across multiple environments (dev, prod)
- Support CI/CD automation

**Decision:**

Use **S3 (private) + CloudFront (OAC) + Route 53** with the following configuration:

1. **S3 Bucket**
   - Private access only (no website hosting enabled)
   - Versioning enabled for rollback capability
   - SSE-S3 encryption
   - Access granted exclusively via CloudFront Origin Access Control (OAC)

2. **CloudFront Distribution**
   - Origin Access Control (OAC) for secure S3 access (SigV4 signing)
   - Custom domain alias (e.g., `dev.example.com`)
   - ACM certificate in us-east-1 (CloudFront requirement)
   - SPA error mappings: 403/404 → `/index.html` with 200 status
   - Cache-optimized settings with compression
   - PriceClass 100 (North America/Europe) for cost efficiency
   - TLS 1.2+, HTTP/2 and HTTP/3, IPv6 enabled

3. **Route 53**
   - Alias A and AAAA records pointing to CloudFront
   - DNS validation for ACM certificates

4. **Cache Strategy**
   - `assets/*` (hashed files): `Cache-Control: public,max-age=31536000,immutable`
   - `index.html`: `Cache-Control: no-cache` (ensures fresh app version)
   - Other root files: `Cache-Control: public,max-age=3600`

**Rationale:**

- **OAC vs OAI:** Origin Access Control replaces the older Origin Access Identity with SigV4 signing and better security posture. This is the current AWS best practice.

- **Private S3 vs Website Hosting:** Private bucket with OAC prevents direct S3 access, forcing all traffic through CloudFront (CDN benefits + potential future WAF/geo-blocking).

- **SPA Error Mappings:** CloudFront's 403/404 error responses are mapped to `index.html` because:
  - S3 returns 403 for non-existent paths when the bucket is private
  - React Router handles client-side routing once the app loads
  - This is simpler than Lambda@Edge for the MVP scope

- **Separate ACM Stack:** CloudFront requires certificates in us-east-1, while the rest of the infrastructure is in eu-west-1. A separate stack with cross-region export/import keeps the architecture clean.

- **PriceClass 100:** Limits edge locations to North America and Europe, reducing cost while covering the primary user base. Can be upgraded to 200 or All later.

**Consequences:**

- **Positive:** Secure by default, CDN-backed, custom domain support, cost-effective, proper SPA routing
- **Negative:** CloudFront distribution creation takes 10-20 minutes; ACM DNS validation can take a few minutes; requires Route 53 for automatic certificate validation

**Alternatives Considered:**

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| S3 Website Hosting (public) | No HTTPS on custom domains, no CDN, direct S3 access |
| Amplify Hosting | Vendor lock-in, less control over cache headers, harder to integrate with existing CloudFormation |
| CloudFront Functions/Lambda@Edge for SPA routing | Overkill for MVP; error mapping is simpler and sufficient |
| Single CloudFront distribution with multiple origins | Separation allows independent cache policies and simpler environment isolation |

**Implementation:**

- Templates: `infrastructure/templates/web-cert-stack.yaml`, `infrastructure/templates/web-stack.yaml`, `infrastructure/templates/teacher-web-stack.yaml`
- Deploy script: `infrastructure/deploy.ps1` (extended with web/web-cert/teacher-web templates)
- CI workflows: `.github/workflows/deploy-web.yml`, `.github/workflows/deploy-teacher-web.yml`

**Teacher vs student region:** The **student** and **teacher** hosting stacks run in **`eu-west-1`**. The **ACM** stack (`web-cert`) stays in **`us-east-1`**; both hosting templates take a **`us-east-1` certificate ARN** as a parameter (CloudFront can attach that ARN regardless of which region creates the distribution).

---

## Addendum (2026-05-03): Unified edge hosting option

**Supplement (not a full ADR rewrite):** The repository may deploy **`StreamMyCourse-EdgeHosting-{env}`** in **`us-east-1`** using [`infrastructure/templates/edge-hosting-stack.yaml`](../../infrastructure/templates/edge-hosting-stack.yaml) — **one** stack with ACM + **both** S3 buckets + **both** CloudFront distributions + Route 53. That removes cross-stack certificate cleanup races at the cost of **larger blast radius** and **S3 objects living in `us-east-1`** (see [`infrastructure/docs/edge-hosting-migration.md`](../../infrastructure/docs/edge-hosting-migration.md)). Legacy templates **`web-cert-stack`**, **`web-stack`**, and **`teacher-web-stack`** remain for brownfield and manual deploys until fully retired.
