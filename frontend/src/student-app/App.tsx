import { Navigate, Route, Routes } from 'react-router-dom'
import CourseCatalogPage from '../pages/CourseCatalogPage'
import CourseDetailPage from '../pages/CourseDetailPage'
import StudentLoginPage from '../pages/StudentLoginPage'
import { PostLoginRedirect } from '../components/auth/PostLoginRedirect'
import { StudentProfileBootstrap } from '../components/auth/StudentProfileBootstrap'
import { StudentLessonAuth } from '../components/auth/StudentLessonAuth'
import { StudentHeader } from './StudentHeader'
import { Layout } from '../components/layout/Layout'

function StudentApp() {
  return (
    <Layout chromeHeader={<StudentHeader />}>
      <PostLoginRedirect />
      <StudentProfileBootstrap />
      <Routes>
        <Route path="/" element={<CourseCatalogPage />} />
        <Route path="/courses/:courseId" element={<CourseDetailPage />} />
        <Route path="/login" element={<StudentLoginPage />} />
        <Route path="/courses/:courseId/lessons/:lessonId" element={<StudentLessonAuth />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default StudentApp
