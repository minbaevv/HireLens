import { useState, useEffect } from 'react'
import api from '../api/client'

export function useAuth() {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [company, setCompany] = useState(null)

  useEffect(() => {
    if (token) {
      api.get('/auth/me')
        .then(r => setCompany(r.data))
        .catch(() => logout())
    }
  }, [token])

  function login(newToken) {
    localStorage.setItem('token', newToken)
    setToken(newToken)
  }

  function logout() {
    localStorage.removeItem('token')
    setToken(null)
    setCompany(null)
  }

  const role = company?.role || null
  const isOwner = !!company?.is_owner
  const isAdmin = role === 'admin'
  const canWrite = role === 'admin' || role === 'recruiter'
  return { token, company, role, isOwner, isAdmin, canWrite, login, logout }
}
