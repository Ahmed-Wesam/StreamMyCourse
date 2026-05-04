import { SignIn } from '../components/auth/SignIn'
import { PostLoginRedirect } from '../components/auth/PostLoginRedirect'
import { Navigate, Route, Routes } from 'react-router-dom'
import InstructorDashboard from '../pages/InstructorDashboard'
import CourseManagement from '../pages/CourseManagement'
import { ProtectedRoute } from '../components/auth/ProtectedRoute'
import { TeacherHeader } from './TeacherHeader'
import { Layout } from '../components/layout/Layout'

function DashboardWrapper() {
  return <InstructorDashboard />
}

function CourseManagementWrapper() {
  return <CourseManagement />
}

function TeacherShell() {
  return (
    <ProtectedRoute>
      <Layout chromeHeader={<TeacherHeader />}>
        <Routes>
          <Route path="/" element={<DashboardWrapper />} />
          <Route path="/courses/:courseId" element={<CourseManagementWrapper />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </ProtectedRoute>
  )
}

function TeacherApp() {
  return (
    <>
      <PostLoginRedirect />
      <SignIn>
        <TeacherShell />
      </SignIn>
    </>
  )
}

export default TeacherApp
