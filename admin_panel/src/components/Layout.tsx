import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useState } from 'react'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  
  const isActive = (path: string) => location.pathname === path

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const canAccessDocuments = user?.role === 'dev' || user?.role === 'admin'
  const canAccessAdminUsers = user?.role === 'dev' || user?.role === 'admin'

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-primary-blue text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold">K1 Manager Admin</h1>
              </div>
              {/* Desktop menu */}
              <div className="hidden md:ml-6 md:flex md:space-x-8">
                <Link
                  to="/users"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    isActive('/users') 
                      ? 'border-primary-yellow text-primary-yellow' 
                      : 'border-transparent text-white hover:border-gray-300 hover:text-gray-300'
                  }`}
                >
                  Пользователи
                </Link>
                {canAccessDocuments && (
                  <Link
                    to="/documents"
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                      isActive('/documents') 
                        ? 'border-primary-yellow text-primary-yellow' 
                        : 'border-transparent text-white hover:border-gray-300 hover:text-gray-300'
                    }`}
                  >
                    Документы
                  </Link>
                )}
                <Link
                  to="/broadcast"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    isActive('/broadcast') 
                      ? 'border-primary-yellow text-primary-yellow' 
                      : 'border-transparent text-white hover:border-gray-300 hover:text-gray-300'
                  }`}
                >
                  Рассылки
                </Link>
                {canAccessAdminUsers && (
                  <Link
                    to="/admin/users"
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                      isActive('/admin/users') 
                        ? 'border-primary-yellow text-primary-yellow' 
                        : 'border-transparent text-white hover:border-gray-300 hover:text-gray-300'
                    }`}
                  >
                    Админ-пользователи
                  </Link>
                )}
              </div>
            </div>
            {/* User info and logout */}
            <div className="flex items-center space-x-4">
              <div className="hidden sm:block text-sm">
                <span className="text-gray-300">{user?.username}</span>
                <span className="text-gray-500 ml-2">({user?.role})</span>
              </div>
              <button
                onClick={handleLogout}
                className="text-white hover:text-gray-300 text-sm"
              >
                Выход
              </button>
              {/* Mobile menu button */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden text-white hover:text-gray-300"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {mobileMenuOpen ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  )}
                </svg>
              </button>
            </div>
          </div>
        </div>
        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden">
            <div className="px-2 pt-2 pb-3 space-y-1">
              <Link
                to="/users"
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-3 py-2 rounded-md text-base font-medium ${
                  isActive('/users')
                    ? 'bg-primary-yellow text-gray-900'
                    : 'text-white hover:bg-gray-700'
                }`}
              >
                Пользователи
              </Link>
              {canAccessDocuments && (
                <Link
                  to="/documents"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`block px-3 py-2 rounded-md text-base font-medium ${
                    isActive('/documents')
                      ? 'bg-primary-yellow text-gray-900'
                      : 'text-white hover:bg-gray-700'
                  }`}
                >
                  Документы
                </Link>
              )}
              <Link
                to="/broadcast"
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-3 py-2 rounded-md text-base font-medium ${
                  isActive('/broadcast')
                    ? 'bg-primary-yellow text-gray-900'
                    : 'text-white hover:bg-gray-700'
                }`}
              >
                Рассылки
              </Link>
              {canAccessAdminUsers && (
                <Link
                  to="/admin/users"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`block px-3 py-2 rounded-md text-base font-medium ${
                    isActive('/admin/users')
                      ? 'bg-primary-yellow text-gray-900'
                      : 'text-white hover:bg-gray-700'
                  }`}
                >
                  Админ-пользователи
                </Link>
              )}
            </div>
          </div>
        )}
      </nav>
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  )
}

