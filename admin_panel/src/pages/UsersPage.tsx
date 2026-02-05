import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { usersApi, User } from '../services/usersApi'
import UserCard from '../components/UserCard'
import { useState } from 'react'

export default function UsersPage() {
  const navigate = useNavigate()
  const [expandedUsers, setExpandedUsers] = useState<Set<number>>(new Set())
  
  const { data: users, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.getAll,
  })
  
  const handleChatClick = (telegramId: number) => {
    navigate(`/chat/${telegramId}`)
  }
  
  const toggleUser = (telegramId: number) => {
    const newExpanded = new Set(expandedUsers)
    if (newExpanded.has(telegramId)) {
      newExpanded.delete(telegramId)
    } else {
      newExpanded.add(telegramId)
    }
    setExpandedUsers(newExpanded)
  }
  
  if (isLoading) {
    return <div className="text-center py-8">Загрузка...</div>
  }
  
  if (error) {
    return <div className="text-center py-8 text-red-600">Ошибка загрузки пользователей</div>
  }
  
  return (
    <div>
      <h1 className="text-3xl font-bold text-primary-blue mb-6">Пользователи</h1>
      
      <div className="card mb-4">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Telegram ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Username</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Телефон</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Onboarding</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Действия</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {users?.map((user) => (
              <tr key={user.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.id}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <a 
                    href={`https://t.me/${user.username || user.telegram_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-blue hover:underline"
                  >
                    {user.telegram_id}
                  </a>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {user.username ? `@${user.username}` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {user.phone ? (
                    <a href={`tel:${user.phone}`} className="text-primary-blue hover:underline">
                      {user.phone}
                    </a>
                  ) : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {user.onboarding_completed === 1 ? (
                    <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                      Завершен
                    </span>
                  ) : (
                    <span className="px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800">
                      В процессе
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <button
                    onClick={() => toggleUser(user.telegram_id)}
                    className="text-primary-blue hover:text-primary-darkBlue mr-2"
                  >
                    {expandedUsers.has(user.telegram_id) ? 'Скрыть' : 'Детали'}
                  </button>
                  <button
                    onClick={() => handleChatClick(user.telegram_id)}
                    className="btn-primary"
                  >
                    Чат
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {users?.map((user) => {
        if (!expandedUsers.has(user.telegram_id)) return null
        
        return (
          <UserCardWithData key={user.telegram_id} user={user} onChatClick={handleChatClick} />
        )
      })}
    </div>
  )
}

function UserCardWithData({ user, onChatClick }: { user: User; onChatClick: (id: number) => void }) {
  const { data: onboardingData } = useQuery({
    queryKey: ['onboarding', user.telegram_id],
    queryFn: () => usersApi.getOnboardingData(user.telegram_id),
  })
  
  return <UserCard user={user} onboardingData={onboardingData} onChatClick={onChatClick} />
}

