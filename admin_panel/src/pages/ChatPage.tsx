import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { messagesApi } from '../services/messagesApi'
import { usersApi } from '../services/usersApi'
import ChatView from '../components/ChatView'
import { useState } from 'react'

export default function ChatPage() {
  const { telegramId } = useParams<{ telegramId: string }>()
  const telegramIdNum = telegramId ? parseInt(telegramId) : 0
  const queryClient = useQueryClient()
  const [messageText, setMessageText] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  
  const { data: user } = useQuery({
    queryKey: ['user', telegramIdNum],
    queryFn: () => usersApi.getById(telegramIdNum),
    enabled: !!telegramIdNum,
  })
  
  const { data: messages, isLoading } = useQuery({
    queryKey: ['messages', telegramIdNum],
    queryFn: () => messagesApi.getUserMessages(telegramIdNum),
    enabled: !!telegramIdNum,
    refetchInterval: 3000, // Обновление каждые 3 секунды
  })
  
  const sendMutation = useMutation({
    mutationFn: async () => {
      await messagesApi.sendMessage({
        telegram_id: telegramIdNum,
        text: messageText,
        file: selectedFile || undefined,
      })
    },
    onSuccess: () => {
      setMessageText('')
      setSelectedFile(null)
      queryClient.invalidateQueries({ queryKey: ['messages', telegramIdNum] })
    },
  })
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (messageText.trim() || selectedFile) {
      sendMutation.mutate()
    }
  }
  
  if (isLoading) {
    return <div className="text-center py-8">Загрузка сообщений...</div>
  }
  
  return (
    <div>
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-primary-blue">
          Чат с пользователем {user?.username ? `@${user.username}` : `#${telegramIdNum}`}
        </h1>
        {user?.phone && (
          <p className="text-gray-600">Телефон: {user.phone}</p>
        )}
      </div>
      
      <div className="card mb-4">
        <ChatView messages={messages || []} />
      </div>
      
      <div className="card">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <textarea
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              placeholder="Введите сообщение..."
              className="input-field"
              rows={3}
            />
          </div>
          <div>
            <input
              type="file"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="input-field"
            />
            {selectedFile && (
              <p className="text-sm text-gray-600 mt-1">Выбран файл: {selectedFile.name}</p>
            )}
          </div>
          <button
            type="submit"
            disabled={sendMutation.isPending || (!messageText.trim() && !selectedFile)}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sendMutation.isPending ? 'Отправка...' : 'Отправить'}
          </button>
        </form>
      </div>
    </div>
  )
}

