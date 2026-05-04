# DynamoDB Integration Plan (Option B)

Replace hardcoded course/lesson data with DynamoDB for real data persistence with course draft/publish workflow and lesson-based video management.

---

## 1. DynamoDB Schema (Single Table Design)

| PK | SK | Attributes | Access Pattern |
|----|-----|------------|----------------|
| `COURSE#<id>` | `METADATA` | title, description, **status** (DRAFT/PUBLISHED), createdAt, updatedAt | Get course details |
| `COURSE#<id>` | `LESSON#<order>` | lessonId, title, **videoKey**, **videoStatus** (pending/processing/ready), duration, createdAt | List course lessons |

**Table Name:** `StreamMyCourse-Catalog-${Environment}`
**Billing:** `PAY_PER_REQUEST` (free tier: 25GB + 200M ops/month)

---

## 2. Infrastructure Changes

### api-stack.yaml additions:
- **DynamoDB Table resource** with PK/SK schema
- **Lambda IAM policy** for DynamoDB read/write (scoped to table only)
- **Environment variable** `TABLE_NAME` passed to Lambda

### No new stacks needed - all in existing api-stack.yaml

---

## 3. Lambda Code Changes (index.py)

### New actions to add:
- `POST /courses` - Create **empty** course (status=DRAFT, no lessons)
- `PUT /courses/:id` - Update course metadata
- `PUT /courses/:id/publish` - Change status from DRAFT → PUBLISHED
- `DELETE /courses/:id` - Delete course + all lessons
- `POST /courses/:id/lessons` - **Create lesson with video upload** (get presigned URL, create lesson record with videoStatus=pending)
- `PUT /courses/:id/lessons/:lessonId` - Update lesson title (not video - video is immutable after upload)
- `DELETE /courses/:id/lessons/:lessonId` - Remove lesson

### Modified actions:
- `list_courses` - Query DynamoDB, **filter PUBLISHED for students**, show all for instructors
- `get_course` - GetItem PK=`COURSE#<id>`, SK=`METADATA` (**404 if DRAFT and not instructor**)
- `list_lessons` - Query PK=`COURSE#<id>`, SK begins_with `LESSON#`
- `get_playback` - Return S3 URL for lesson's **videoKey** (check lesson.videoStatus=ready)

### Configuration:
- **`TABLE_NAME` required** in deployed Lambda; without it the handler returns **503** `catalog_unconfigured` (no in-process mock catalog).

---

## 4. Frontend Changes

### New page: InstructorDashboard.tsx
- List instructor's courses with status badges (DRAFT/PUBLISHED)
- Create new **empty** course button → form (title, description only)
- **Course cards show:** title, status, lesson count, publish button (if DRAFT and has lessons)

### New page: CourseManagement.tsx (replaces generic editor)
- **Course info section:** Edit title/description, status badge, publish button (only if has ready lessons)
- **Lessons list:** Show all lessons with video status
- **"Add Lesson" flow:**
  1. Click "Add Lesson" → form (title, video file)
  2. Call `POST /courses/:id/lessons` → get presigned URL
  3. Upload video directly to S3
  4. Lesson created with videoStatus=pending → updates to ready when processed
- **Per lesson actions:** Edit title, Delete lesson (only if course is DRAFT)

### Removed: Standalone InstructorUploadPage
- Upload now happens **within course context** via CourseManagement page
- No orphaned uploads - every video belongs to a lesson

---

## 5. API Design (New Endpoints)

```
POST   /courses                      → Create empty course (status=DRAFT)
GET    /courses                      → List courses (students see PUBLISHED only)
GET    /courses/:id                   → Get course (404 if DRAFT and not owner)
PUT    /courses/:id                   → Update course metadata
PUT    /courses/:id/publish           → Publish course (DRAFT → PUBLISHED)
DELETE /courses/:id                   → Delete course + all lessons

GET    /courses/:id/lessons           → List lessons
POST   /courses/:id/lessons           → Create lesson with presigned URL
                                       Returns: {lessonId, uploadUrl, videoKey}
PUT    /courses/:id/lessons/:lid     → Update lesson title only
DELETE /courses/:id/lessons/:lid     → Delete lesson (only in DRAFT)

GET    /playback/:cid/:lid           → Get video URL (checks lesson.videoStatus=ready)
```

---

## 6. Work Breakdown (Implementation Order)

1. **Infrastructure** - Add DynamoDB table to api-stack.yaml, add IAM permissions, deploy
2. **Lambda course CRUD** - POST/PUT/DELETE courses with DRAFT/PUBLISHED status
3. **Lambda lesson CRUD** - POST creates lesson + returns presigned URL, PUT/DELETE for management
4. **Lambda read operations** - Update list_courses, get_course, list_lessons with status filtering
5. **Frontend InstructorDashboard** - List courses, create empty course, publish button
6. **Frontend CourseManagement** - Course editor + lesson list + "Add Lesson" flow with upload
7. **Remove old pages** - Delete InstructorUploadPage, integrate into CourseManagement

---

## 7. Cost Analysis (Free Tier)

| Service | Free Tier | MVP Usage |
|---------|-----------|-----------|
| DynamoDB | 25 GB + 200M reads/writes/month | ~100 courses × 5 lessons = 500 items, negligible ops |
| S3 | 5 GB | Video storage (separate from DB) |
| Lambda | 1M requests + 400K GB-s | ~1000 requests/day |
| **Total** | | **$0** |

---

## 8. Testing Strategy

- **Local:** Use a dev stack or LocalStack with `TABLE_NAME` set; frontend requires `VITE_API_BASE_URL` (see `frontend/.env.example`).
- **Integration:** Deploy to dev, use AWS Console to verify data written correctly
- **Upload flow:** Test full flow: create course → upload video → lesson appears → play video

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| DynamoDB eventually consistent reads | Use `ConsistentRead: true` for lessons list (strong consistency) |
| UUID collision | Use `uuid4()` - astronomically unlikely |
| Large scan operations | Add GSI later if we need to query by instructor (when auth added) |

---

**Key Workflow Changes:**
1. Courses are created **empty** (0 lessons, DRAFT status)
2. Instructor adds lessons **one at a time** with video upload
3. Each lesson has a **videoStatus**: pending → ready (after S3 upload succeeds)
4. Course can be **published** only when it has at least one ready lesson
5. Published courses are visible to students; draft courses are instructor-only

**Decision needed:** Do we proceed with this updated plan?
