import React, { lazy, Suspense } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import { configureAmplify } from './lib/auth'
import './style.css'
import './styles/prototype-base.css'

configureAmplify()

const StudentApp = lazy(() => import('./student-app/App'))

void import('./lib/install-session-superseded-rejection-handler').then(
  ({ installSessionSupersededRejectionHandler }) => {
    installSessionSupersededRejectionHandler()
  },
)

ReactDOM.createRoot(document.getElementById('app')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Suspense fallback={null}>
        <StudentApp />
      </Suspense>
    </BrowserRouter>
  </React.StrictMode>,
)
