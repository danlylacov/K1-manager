import { User, OnboardingData } from '../services/usersApi'

interface UserCardProps {
  user: User
  onboardingData?: OnboardingData
  onChatClick: (telegramId: number) => void
}

export default function UserCard({ user, onboardingData, onChatClick }: UserCardProps) {
  const telegramLink = `https://t.me/${user.username || user.telegram_id}`
  
  return (
    <div className="card mb-4">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-primary-blue">
            Пользователь #{user.id}
          </h3>
          <p className="text-sm text-gray-600">
            Telegram ID: <a href={telegramLink} target="_blank" rel="noopener noreferrer" className="text-primary-blue hover:underline">
              {user.telegram_id}
            </a>
          </p>
          {user.username && (
            <p className="text-sm text-gray-600">Username: @{user.username}</p>
          )}
          {user.phone && (
            <p className="text-sm text-gray-600">Телефон: <a href={`tel:${user.phone}`} className="text-primary-blue hover:underline">{user.phone}</a></p>
          )}
        </div>
        <button
          onClick={() => onChatClick(user.telegram_id)}
          className="btn-primary"
        >
          Открыть чат
        </button>
      </div>
      
      {onboardingData && (
        <div className="border-t pt-4 mt-4">
          <h4 className="font-semibold mb-3 text-primary-blue">Данные onboarding</h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-primary-lightYellow p-3 rounded">
              <p className="text-sm font-medium text-gray-700">Навык работы с мышкой/клавиатурой</p>
              <p className="text-sm text-gray-900 mt-1">
                {onboardingData.extracted.mouse_keyboard_skill || 'Не указано'}
              </p>
            </div>
            <div className="bg-primary-lightYellow p-3 rounded">
              <p className="text-sm font-medium text-gray-700">Опыт программирования</p>
              <p className="text-sm text-gray-900 mt-1">
                {onboardingData.extracted.programming_experience || 'Не указано'}
              </p>
            </div>
            <div className="bg-primary-lightYellow p-3 rounded">
              <p className="text-sm font-medium text-gray-700">Возраст ребенка</p>
              <p className="text-sm text-gray-900 mt-1">
                {onboardingData.extracted.child_age || 'Не указано'}
              </p>
            </div>
            <div className="bg-primary-lightYellow p-3 rounded">
              <p className="text-sm font-medium text-gray-700">Имя ребенка</p>
              <p className="text-sm text-gray-900 mt-1">
                {onboardingData.extracted.child_name || 'Не указано'}
              </p>
            </div>
          </div>
          
          {onboardingData.needs_clarification && (
            <div className="mt-4 bg-yellow-100 border-l-4 border-primary-yellow p-3 rounded">
              <p className="text-sm font-medium text-gray-800">Требуется уточнение</p>
              {onboardingData.clarification_question && (
                <p className="text-sm text-gray-700 mt-1">{onboardingData.clarification_question}</p>
              )}
            </div>
          )}
          
          {!onboardingData.needs_clarification && (
            <div className="mt-4 bg-green-100 border-l-4 border-green-500 p-3 rounded">
              <p className="text-sm font-medium text-gray-800">Onboarding завершен</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

