import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  getCourse,
  updateCourse,
  listLessons,
  deleteLesson,
  listCourseModules,
  createCourseModule,
  deleteCourseModule,
  getUploadUrl,
  markCourseThumbnailReady,
  publishCourse,
  ApiError,
  type Course,
  type CourseModule,
  type Lesson,
} from '../lib/api'
import { createAndUploadDraftLesson } from '../lib/courseManagementLessonUpload'
import { moduleDeleteFailureMessage } from '../lib/courseManagementModuleErrors'
import { CourseThumbnailEditor } from '../components/course/CourseThumbnailEditor'
import { CourseManagementAddLessonModal } from '../components/course/CourseManagementAddLessonModal'
import { CourseManagementLessonsPanel } from '../components/course/CourseManagementLessonsPanel'
import { CourseManagementModulesPanel } from '../components/course/CourseManagementModulesPanel'
import {
  CourseManagementLoadError,
  CourseManagementLoadingSkeleton,
  CourseManagementNotFound,
} from '../components/course/CourseManagementPageStates'

export default function CourseManagement() {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const [course, setCourse] = useState<Course | null>(null)
  const [lessons, setLessons] = useState<Lesson[]>([])
  const [modules, setModules] = useState<CourseModule[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [info, setInfo] = useState<string | null>(null)

  const [editTitle, setEditTitle] = useState('')
  const [editDescription, setEditDescription] = useState('')

  const [showAddLesson, setShowAddLesson] = useState(false)
  const [newLessonTitle, setNewLessonTitle] = useState('')
  const [selectedModuleId, setSelectedModuleId] = useState<string>('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)

  const [thumbFile, setThumbFile] = useState<File | null>(null)
  const [thumbUploading, setThumbUploading] = useState(false)

  const [newModuleTitle, setNewModuleTitle] = useState('')
  const [newModuleDescription, setNewModuleDescription] = useState('')

  const loadCourseData = useCallback(async (): Promise<boolean> => {
    if (!courseId) return false

    try {
      setLoading(true)
      setError(null)
      setNotFound(false)
      setInfo(null)
      const [courseData, lessonsData, modulesData] = await Promise.all([
        getCourse(courseId),
        listLessons(courseId),
        listCourseModules(courseId),
      ])

      if (!courseData) {
        setCourse(null)
        setLessons([])
        setModules([])
        setEditTitle('')
        setEditDescription('')
        setSelectedModuleId('')
        setNotFound(true)
        setError(null)
      } else {
        setCourse(courseData)
        setLessons(lessonsData)
        setModules(modulesData)
        setEditTitle(courseData.title)
        setEditDescription(courseData.description)
        if (modulesData.length > 0) {
          setSelectedModuleId((prev) => (prev && modulesData.some((m) => m.id === prev) ? prev : modulesData[0].id))
        } else {
          setSelectedModuleId('')
        }
      }
      return true
    } catch (err) {
      setCourse(null)
      setLessons([])
      setModules([])
      setEditTitle('')
      setEditDescription('')
      setSelectedModuleId('')
      const is404 = err instanceof ApiError && err.status === 404
      setNotFound(is404)
      setError(is404 ? null : err instanceof Error ? err.message : 'Failed to load course')
      return false
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
      const lessonInput =
        modules.length > 1 && selectedModuleId
          ? { title: newLessonTitle, moduleId: selectedModuleId }
          : { title: newLessonTitle }
      await createAndUploadDraftLesson({
        courseId,
        lessonInput,
        videoFile: selectedFile,
        onUploadProgress: setUploadProgress,
      })
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

  const handleCreateModule = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!courseId || !newModuleTitle.trim()) return

    try {
      setError(null)
      setInfo(null)
      await createCourseModule(courseId, { title: newModuleTitle.trim(), description: newModuleDescription })
      setNewModuleTitle('')
      setNewModuleDescription('')
      await loadCourseData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create module')
    }
  }

  const handleDeleteModule = async (moduleId: string) => {
    if (!courseId || !confirm('Are you sure you want to delete this module?')) return

    try {
      setError(null)
      setInfo(null)
      const res = await deleteCourseModule(courseId, moduleId)
      const reloadOk = await loadCourseData()
      if (res.deleted === false) {
        if (reloadOk) {
          setInfo('Module already removed; refreshing list')
        } else {
          setError('That module was already removed. Could not refresh the course.')
        }
      }
    } catch (err) {
      const mapped = moduleDeleteFailureMessage(err)
      setError(mapped ?? (err instanceof Error ? err.message : 'Failed to delete module'))
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
    return <CourseManagementLoadingSkeleton />
  }

  if (notFound) {
    return <CourseManagementNotFound onBack={navigate} />
  }

  if (error && !course) {
    return <CourseManagementLoadError error={error} onBack={navigate} />
  }

  if (!course) {
    return <CourseManagementNotFound onBack={navigate} />
  }

  const sortedModules = [...modules].sort((a, b) => a.order - b.order)
  const sortedLessons = [...lessons].sort((a, b) => a.moduleOrder - b.moduleOrder || a.order - b.order)
  const moduleTitleById = new Map(sortedModules.map((m) => [m.id, m.title]))

  const readyLessons = sortedLessons.filter((l) => l.videoStatus === 'ready').length
  const canPublish = course.status === 'DRAFT' && readyLessons > 0

  const handlePublishCourse = async () => {
    if (!courseId) return
    try {
      setError(null)
      await publishCourse(courseId)
      const reloadOk = await loadCourseData()
      if (reloadOk) {
        navigate('/')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish course')
    }
  }

  const closeAddLessonModal = () => {
    setShowAddLesson(false)
    setNewLessonTitle('')
    setSelectedModuleId(sortedModules[0]?.id ?? '')
    setSelectedFile(null)
    setUploadProgress(0)
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-blue-600 hover:text-blue-800 text-sm mb-2"
          >
            ← Back to Dashboard
          </button>
          <h1 className="text-3xl font-bold text-gray-900">Manage Course</h1>
        </div>
        <span
          className={`px-4 py-2 rounded-full text-sm font-medium ${
            course.status === 'PUBLISHED' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
          }`}
        >
          {course.status}
        </span>
      </div>

      {error && (
        <div
          className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700"
          data-testid="course-management-inline-error"
          role="alert"
        >
          {error}
        </div>
      )}

      {info && (
        <div
          className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4 text-blue-700"
          data-testid="course-management-inline-info"
          role="status"
        >
          {info}
        </div>
      )}

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
              type="button"
              onClick={() => void handleSaveCourse()}
              disabled={saving}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
            {canPublish && (
              <button
                type="button"
                onClick={() => void handlePublishCourse()}
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

      {course.status === 'DRAFT' && (
        <CourseManagementModulesPanel
          sortedModules={sortedModules}
          newModuleTitle={newModuleTitle}
          newModuleDescription={newModuleDescription}
          onNewModuleTitleChange={setNewModuleTitle}
          onNewModuleDescriptionChange={setNewModuleDescription}
          onCreateModule={handleCreateModule}
          onDeleteModule={handleDeleteModule}
        />
      )}

      <CourseManagementLessonsPanel
        course={course}
        sortedLessons={sortedLessons}
        moduleTitleById={moduleTitleById}
        onAddLessonClick={() => setShowAddLesson(true)}
        onDeleteLesson={handleDeleteLesson}
      />

      {showAddLesson && (
        <CourseManagementAddLessonModal
          sortedModules={sortedModules}
          newLessonTitle={newLessonTitle}
          selectedModuleId={selectedModuleId}
          selectedFile={selectedFile}
          uploading={uploading}
          uploadProgress={uploadProgress}
          onNewLessonTitleChange={setNewLessonTitle}
          onSelectedModuleIdChange={setSelectedModuleId}
          onFileChange={handleFileChange}
          onSubmit={handleAddLesson}
          onCancel={closeAddLessonModal}
        />
      )}
    </div>
  )
}
