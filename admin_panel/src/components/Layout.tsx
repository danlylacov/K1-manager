import { Link, useLocation } from 'react-router-dom'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  
  const isActive = (path: string) => location.pathname === path

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-primary-blue text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold">K1 Manager Admin</h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
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
              </div>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  )
}

