import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { installSessionSupersededRejectionHandler } from './lib/install-session-superseded-rejection-handler'
import StudentApp from './student-app/App'
import './style.css'

installSessionSupersededRejectionHandler()

ReactDOM.createRoot(document.getElementById('app')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <StudentApp />
    </BrowserRouter>
  </React.StrictMode>,
)
