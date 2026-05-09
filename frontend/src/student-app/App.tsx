import { Navigate, Route, Routes } from 'react-router-dom'
import CourseCatalogPage from '../pages/CourseCatalogPage'
import CourseDetailPage from '../pages/CourseDetailPage'
import CoursePage from '../pages/CoursePage'
import HomePage from '../pages/HomePage'
import LearnRedirectPage from '../pages/LearnRedirectPage'
import MyCoursePage from '../pages/MyCoursePage'
import StudentLoginPage from '../pages/StudentLoginPage'
import { PostLoginRedirect } from '../components/auth/PostLoginRedirect'
import { StudentProfileBootstrap } from '../components/auth/StudentProfileBootstrap'
import { StudentLessonAuth } from '../components/auth/StudentLessonAuth'
import { StudentHeader } from './StudentHeader'
import { Layout } from '../components/layout/Layout'
import { ScrollToTop } from './ScrollToTop'

function StudentApp() {
  return (
    <Layout chromeHeader={<StudentHeader />}>
      <ScrollToTop />
      <PostLoginRedirect />
      <StudentProfileBootstrap />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/course" element={<CoursePage />} />
        <Route path="/learn" element={<LearnRedirectPage />} />
        <Route path="/catalog" element={<CourseCatalogPage />} />
        <Route path="/my-course" element={<MyCoursePage />} />
        <Route path="/courses/:courseId" element={<CourseDetailPage />} />
        <Route path="/login" element={<StudentLoginPage />} />
        <Route path="/courses/:courseId/lessons/:lessonId" element={<StudentLessonAuth />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default StudentApp
