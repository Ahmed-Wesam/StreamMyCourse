# Unified edge hosting stack (migration)

## Status: COMPLETED (2026-05-03)

Cutover is done: student and teacher custom domains resolve to **`StreamMyCourse-EdgeHosting-{env}`** in **`us-east-1`**. Legacy **`StreamMyCourse-Web-*`**, **`StreamMyCourse-TeacherWeb-*`**, and **`StreamMyCourse-Cert-*`** stacks were removed. CI/CD uses **[`.github/workflows/deploy-backend.yml`](../../.github/workflows/deploy-backend.yml)** with **`AttachCloudFrontAliases=true`** by default (no `EDGE_ATTACH_CF_ALIASES=false` override). Legacy templates and manual SPA workflows were removed from the repo; SPA deploys use **`deploy-web-reusable.yml`** / **`deploy-teacher-web-reusable.yml`** only via the main Deploy workflow.

The sections below remain as **historical** reference for brownfield accounts repeating a similar migration.

---

**CloudFront CNAME conflict (409):** An alternate domain name can be attached to **only one** distribution per account. If legacy **`StreamMyCourse-Web-*`** / **`TeacherWeb-*`** CloudFront distributions still list the same student and teacher hostnames you pass into the edge stack, **`AttachCloudFrontAliases=true`** fails with *CNAMEs you provided are already associated with a different resource*. Until you remove those aliases (or delete the legacy stacks), deploy with **`AttachCloudFrontAliases=false`** (e.g. export **`EDGE_ATTACH_CF_ALIASES=false`** for `deploy-edge.sh`, or **`deploy.ps1 -AttachCloudFrontAliases false`**). Distributions then use **`*.cloudfront.net`** only; SPA deploy and invalidation still work via stack outputs. After cutover, flip to **`true`** and update once Route 53 is ready.

**Warning:** Do not create **duplicate Route 53** alias records for the same names while legacy stacks still own those record sets — CloudFormation can fail or leave DNS inconsistent. Follow the order below (or use **new** hostnames for a dry run).

`StreamMyCourse-EdgeHosting-{dev|prod}` in **`us-east-1`** replaces the three-stack pattern:

- `StreamMyCourse-Cert-{env}` (ACM only)
- `StreamMyCourse-Web-{env}` (student S3 + CloudFront + R53 in `eu-west-1`)
- `StreamMyCourse-TeacherWeb-{env}` (teacher S3 + CloudFront + R53 in `eu-west-1`)

## Why

One CloudFormation graph ties **ACM certificate replacement** to **both CloudFront distributions**, so cleanup does not try to delete an old certificate while another stack still attaches it.

## Bucket names

The unified template uses **region-suffixed** global bucket names (e.g. `streammycourse-site-dev-us-east-1-{account}`) so it can be created **alongside** legacy `eu-west-1` buckets during migration. SPA deploy workflows read **outputs** from the edge stack; no hard-coded bucket names in CI.

## Migration order (dev, then prod)

1. **Lower TTL** on student/teacher DNS names if you need fast rollback (optional).
2. **Deploy** `StreamMyCourse-EdgeHosting-{env}` with **`AttachCloudFrontAliases=false`** while legacy CloudFront still holds the hostnames; use **`AttachCloudFrontAliases=true`** only after those aliases are released (e.g. `.\deploy.ps1 -Template edge-hosting -StackName StreamMyCourse-EdgeHosting-dev -Environment dev -Region eu-west-1 -DomainName ... -TeacherDomainName ... -HostedZoneId ... -AttachCloudFrontAliases false` — `Region` is overridden to `us-east-1` for this template).
3. **Wait** for ACM **Issued** and CloudFront **Deployed**.
4. **Sync objects** from old student/teacher buckets in `eu-west-1` to the new output bucket names (`aws s3 sync` with `--region us-east-1` on the destination side).
5. **Remove Route 53 records** owned by the old web/teacher stacks (or delete those stacks) so the new stack’s records are the only ones for the same names — **two stacks cannot own the same record set**.
6. **Merge / push** workflow changes that read outputs from `StreamMyCourse-EdgeHosting-*` and run **student + teacher** SPA deploys.
7. **Delete** legacy stacks when confident: `StreamMyCourse-Cert-*`, `StreamMyCourse-Web-*`, `StreamMyCourse-TeacherWeb-*` (empty buckets first if policies require).

## IAM

After any change to [`infrastructure/iam-policy-github-deploy-web.json`](../iam-policy-github-deploy-web.json), run `.\scripts\apply-github-deploy-role-policies.ps1` so GitHub Actions can `DescribeStacks` on the new stack in `us-east-1`.

## Rollback

Keep old stacks until cutover succeeds. If you must roll back DNS, point aliases back at the old distributions before deleting legacy stacks.
