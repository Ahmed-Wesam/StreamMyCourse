import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  getCourse,
  updateCourse,
  listLessons,
  createLesson,
  deleteLesson,
  getUploadUrl,
  markLessonVideoReady,
  markCourseThumbnailReady,
  publishCourse,
  type Course,
  type Lesson,
} from '../lib/api'
import { CourseThumbnailEditor } from '../components/course/CourseThumbnailEditor'
import { captureFrameAtVideoPercent } from '../lib/videoThumbnail'

export default function CourseManagement() {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const [course, setCourse] = useState<Course | null>(null)
  const [lessons, setLessons] = useState<Lesson[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Edit course form
  const [editTitle, setEditTitle] = useState('')
  const [editDescription, setEditDescription] = useState('')

  // Add lesson modal
  const [showAddLesson, setShowAddLesson] = useState(false)
  const [newLessonTitle, setNewLessonTitle] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)

  const [thumbFile, setThumbFile] = useState<File | null>(null)
  const [thumbUploading, setThumbUploading] = useState(false)

  const loadCourseData = useCallback(async () => {
    if (!courseId) return

    try {
      setLoading(true)
      setError(null)
      const [courseData, lessonsData] = await Promise.all([
        getCourse(courseId),
        listLessons(courseId),
      ])
      setCourse(courseData)
      setLessons(lessonsData)
      setEditTitle(courseData.title)
      setEditDescription(courseData.description)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load course')
    } finally {
      setLoading(false)
    }
  }, [courseId])

  useEffect(() => {
    if (courseId) {
      void loadCourseData()
    }
  }, [courseId, loadCourseData])

  const handleSaveCourse = async () => {
    if (!courseId) return

    setSaving(true)
    setError(null)

    try {
      await updateCourse(courseId, {
        title: editTitle,
        description: editDescription,
      })
      await loadCourseData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update course')
    } finally {
      setSaving(false)
    }
  }

  const handleAddLesson = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!courseId || !newLessonTitle.trim() || !selectedFile) return

    setUploading(true)
    setUploadProgress(10)
    setError(null)

    try {
      // Step 1: Create lesson
      setUploadProgress(20)
      const lessonResult = await createLesson(courseId, { title: newLessonTitle })

      // Step 2: Get presigned URL (must match the Content-Type header on PUT; empty file.type breaks the signature)
      setUploadProgress(30)
      const contentType = selectedFile.type || 'video/mp4'
      const { uploadUrl } = await getUploadUrl(selectedFile.name, contentType, {
        courseId,
        lessonId: lessonResult.lessonId,
      })

      // Step 3: Upload to S3
      setUploadProgress(40)
      const xhr = new XMLHttpRequest()

      await new Promise((resolve, reject) => {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 50) + 40
            setUploadProgress(percent)
          }
        })

        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(null)
          } else {
            reject(new Error(`Upload failed: ${xhr.statusText}`))
          }
        })

        xhr.addEventListener('error', () => reject(new Error('Upload failed')))
        xhr.addEventListener('abort', () => reject(new Error('Upload aborted')))

        xhr.open('PUT', uploadUrl, true)
        xhr.setRequestHeader('Content-Type', contentType)
        xhr.send(selectedFile)
      })

      // Step 4: Auto thumbnail at 20% of duration (no separate image upload in MVP)
      setUploadProgress(92)
      let lessonThumbKey: string | undefined
      try {
        const jpeg = await captureFrameAtVideoPercent(selectedFile, 0.2)
        const thumb = await getUploadUrl('lesson-thumb.jpg', 'image/jpeg', {
          courseId,
          lessonId: lessonResult.lessonId,
          uploadKind: 'lessonThumbnail',
        })
        if (thumb.thumbnailKey) {
          const putThumb = await fetch(thumb.uploadUrl, {
            method: 'PUT',
            body: jpeg,
            headers: { 'Content-Type': 'image/jpeg' },
          })
          if (putThumb.ok) {
            lessonThumbKey = thumb.thumbnailKey
          }
        }
      } catch {
        // Continue without lesson thumbnail if decode/seek fails (e.g. unsupported codec in browser)
      }

      // Step 5: Mark lesson video ready
      setUploadProgress(95)
      await markLessonVideoReady(
        courseId,
        lessonResult.lessonId,
        lessonThumbKey ? { thumbnailKey: lessonThumbKey } : undefined,
      )

      setUploadProgress(100)
      setShowAddLesson(false)
      setNewLessonTitle('')
      setSelectedFile(null)
      await loadCourseData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add lesson')
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
  }

  const handleDeleteLesson = async (lessonId: string) => {
    if (!courseId || !confirm('Are you sure you want to delete this lesson?')) return

    try {
      setError(null)
      await deleteLesson(courseId, lessonId)
      await loadCourseData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete lesson')
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.type.startsWith('video/')) {
      setSelectedFile(file)
      setError(null)
    } else if (file) {
      setError('Please select a valid video file')
    }
  }

  const handleThumbFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.type.startsWith('image/')) {
      setThumbFile(file)
      setError(null)
    } else if (file) {
      setError('Please select a valid image (JPEG, PNG, or WebP).')
    }
  }

  const handleThumbnailUpload = async () => {
    if (!courseId || !thumbFile) return
    setThumbUploading(true)
    setError(null)
    try {
      const contentType = thumbFile.type || 'image/jpeg'
      const { uploadUrl, thumbnailKey } = await getUploadUrl(thumbFile.name, contentType, {
        courseId,
        uploadKind: 'thumbnail',
      })
      if (!thumbnailKey) {
        throw new Error('No thumbnail key returned from server')
      }
      const putRes = await fetch(uploadUrl, {
        method: 'PUT',
        headers: { 'Content-Type': contentType },
        body: thumbFile,
      })
      if (!putRes.ok) {
        throw new Error(`Thumbnail upload failed: ${putRes.status}`)
      }
      await markCourseThumbnailReady(courseId, thumbnailKey)
      setThumbFile(null)
      await loadCourseData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload thumbnail')
    } finally {
      setThumbUploading(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl">
        <div className="animate-pulse">
          <div className="mb-8 h-8 w-1/3 rounded bg-gray-200" />
          <div className="mb-6 h-32 rounded-lg bg-gray-200" />
          <div className="h-64 rounded-lg bg-gray-200" />
        </div>
      </div>
    )
  }

  if (!course) {
    return (
      <div className="mx-auto max-w-4xl text-center">
        <h1 className="mb-4 text-2xl font-bold text-gray-900">Course not found</h1>
        <button
          type="button"
          onClick={() => navigate('/')}
          className="rounded-lg bg-blue-600 px-6 py-2 text-white transition-colors hover:bg-blue-700"
        >
          Back to Dashboard
        </button>
      </div>
    )
  }

  const readyLessons = lessons.filter((l) => l.videoStatus === 'ready').length
  const canPublish = course.status === 'DRAFT' && readyLessons > 0

  const handlePublishCourse = async () => {
    if (!courseId) return
    try {
      setError(null)
      await publishCourse(courseId)
      await loadCourseData()
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish course')
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
          <button
            onClick={() => navigate('/')}
            className="text-blue-600 hover:text-blue-800 text-sm mb-2"
          >
            ← Back to Dashboard
          </button>
            <h1 className="text-3xl font-bold text-gray-900">Manage Course</h1>
          </div>
          <span
            className={`px-4 py-2 rounded-full text-sm font-medium ${
              course.status === 'PUBLISHED'
                ? 'bg-green-100 text-green-800'
                : 'bg-yellow-100 text-yellow-800'
            }`}
          >
            {course.status}
          </span>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Course Info Section */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Course Information</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleSaveCourse}
                disabled={saving}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              {canPublish && (
                <button
                  onClick={handlePublishCourse}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  Publish Course
                </button>
              )}
            </div>
          </div>
        </div>

        <CourseThumbnailEditor
          course={course}
          thumbFile={thumbFile}
          thumbUploading={thumbUploading}
          onThumbFileChange={handleThumbFileChange}
          onUpload={() => void handleThumbnailUpload()}
        />

        {/* Lessons Section */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">
              Lessons ({lessons.length})
            </h2>
            {course.status === 'DRAFT' && (
              <button
                onClick={() => setShowAddLesson(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                + Add Lesson
              </button>
            )}
          </div>

          {lessons.length === 0 ? (
            <div className="rounded-lg bg-gray-50 py-12 text-center">
              <p className="text-gray-600">No lessons yet</p>
              {course.status === 'DRAFT' && (
                <p className="text-sm text-gray-500 mt-1">Add your first lesson with a video</p>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {lessons.map((lesson, index) => (
                <div
                  key={lesson.id}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <span className="text-gray-400 font-medium">{index + 1}</span>
                    <div>
                      <h3 className="font-medium text-gray-900">{lesson.title}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span
                          className={`text-xs px-2 py-1 rounded ${
                            lesson.videoStatus === 'ready'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-yellow-100 text-yellow-700'
                          }`}
                        >
                          {lesson.videoStatus === 'ready' ? '✓ Ready' : '⏳ Pending'}
                        </span>
                      </div>
                    </div>
                  </div>
                  {course.status === 'DRAFT' && (
                    <button
                      onClick={() => handleDeleteLesson(lesson.id)}
                      className="text-red-600 hover:text-red-800 text-sm px-3 py-1 hover:bg-red-50 rounded transition-colors"
                    >
                      Delete
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Add Lesson Modal */}
        {showAddLesson && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-md w-full p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Add New Lesson</h2>
              <form onSubmit={handleAddLesson}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Lesson Title *
                  </label>
                  <input
                    type="text"
                    value={newLessonTitle}
                    onChange={(e) => setNewLessonTitle(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="e.g., Introduction"
                    required
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Video File *
                  </label>
                  <input
                    type="file"
                    accept="video/*"
                    onChange={handleFileChange}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                  {selectedFile && (
                    <p className="text-sm text-gray-600 mt-2">
                      Selected: {selectedFile.name} ({Math.round(selectedFile.size / 1024 / 1024)}MB)
                    </p>
                  )}
                </div>

                {uploading && (
                  <div className="mb-4">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                      <span>Uploading...</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all"
                        style={{ width: `${uploadProgress}%` }}
                      ></div>
                    </div>
                  </div>
                )}

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowAddLesson(false)
                      setNewLessonTitle('')
                      setSelectedFile(null)
                      setUploadProgress(0)
                    }}
                    disabled={uploading}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={uploading || !newLessonTitle.trim() || !selectedFile}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                  >
                    {uploading ? 'Uploading...' : 'Add Lesson'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
    </div>
  )
}
