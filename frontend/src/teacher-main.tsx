import React, { lazy, Suspense } from 'react'
import ReactDOM from 'react-dom/client'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { BrowserRouter } from 'react-router-dom'

import { configureAmplify } from './lib/auth'
import './style.css'

configureAmplify()

const TeacherApp = lazy(() => import('./teacher-app/App'))

ReactDOM.createRoot(document.getElementById('app')!).render(
  <React.StrictMode>
    <AuthenticatorProvider>
      <BrowserRouter>
        <Suspense fallback={null}>
          <TeacherApp />
        </Suspense>
      </BrowserRouter>
    </AuthenticatorProvider>
  </React.StrictMode>,
)
