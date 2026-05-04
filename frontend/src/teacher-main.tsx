import React from 'react'
import ReactDOM from 'react-dom/client'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { BrowserRouter } from 'react-router-dom'
import TeacherApp from './teacher-app/App'
import { configureAmplify } from './lib/auth'
import './style.css'

configureAmplify()

ReactDOM.createRoot(document.getElementById('app')!).render(
  <React.StrictMode>
    <AuthenticatorProvider>
      <BrowserRouter>
        <TeacherApp />
      </BrowserRouter>
    </AuthenticatorProvider>
  </React.StrictMode>,
)
