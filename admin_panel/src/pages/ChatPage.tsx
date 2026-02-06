import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { messagesApi } from '../services/messagesApi'
import { usersApi } from '../services/usersApi'
import ChatView from '../components/ChatView'
import EmojiPicker from '../components/EmojiPicker'
import { useState } from 'react'

export default function ChatPage() {
  const { telegramId } = useParams<{ telegramId: string }>()
  const telegramIdNum = telegramId ? parseInt(telegramId) : 0
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [messageText, setMessageText] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  
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
        files: selectedFiles.length > 0 ? selectedFiles : undefined,
      })
    },
    onSuccess: () => {
      setMessageText('')
      setSelectedFiles([])
      queryClient.invalidateQueries({ queryKey: ['messages', telegramIdNum] })
    },
  })
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (messageText.trim() || selectedFiles.length > 0) {
      sendMutation.mutate()
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const filesArray = Array.from(e.target.files)
      setSelectedFiles((prev) => [...prev, ...filesArray])
    }
  }

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const isImageFile = (file: File) => {
    return file.type.startsWith('image/')
  }
  
  if (isLoading) {
    return <div className="text-center py-8">Загрузка сообщений...</div>
  }
  
  return (
    <div>
      <div className="mb-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-4 mb-2 space-y-2 sm:space-y-0">
          <button
            onClick={() => navigate('/users')}
            className="btn-secondary text-sm w-full sm:w-auto"
          >
            ← Назад
          </button>
          <h1 className="text-xl sm:text-2xl font-bold text-primary-blue">
            Чат с пользователем {user?.username ? `@${user.username}` : `#${telegramIdNum}`}
          </h1>
        </div>
        {user?.phone && (
          <p className="text-sm sm:text-base text-gray-600">Телефон: {user.phone}</p>
        )}
      </div>
      
      <div className="card mb-4">
        <ChatView messages={messages || []} />
      </div>
      
      <div className="card">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <textarea
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              placeholder="Введите сообщение..."
              className="input-field pr-10"
              rows={3}
            />
            <div className="absolute bottom-2 right-2">
              <EmojiPicker
                onEmojiSelect={(emoji) => {
                  setMessageText((prev) => prev + emoji)
                }}
              />
            </div>
          </div>
          <div>
            <input
              type="file"
              multiple
              accept="image/*"
              onChange={handleFileChange}
              className="input-field"
            />
            {selectedFiles.length > 0 && (
              <div className="mt-2 space-y-2">
                {selectedFiles.map((file, index) => (
                  <div key={index} className="flex items-center space-x-2 p-2 bg-gray-100 rounded">
                    {isImageFile(file) && (
                      <img
                        src={URL.createObjectURL(file)}
                        alt={file.name}
                        className="w-16 h-16 object-cover rounded"
                      />
                    )}
                    <div className="flex-1">
                      <p className="text-sm text-gray-700">{file.name}</p>
                      <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeFile(index)}
                      className="text-red-600 hover:text-red-800"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          <button
            type="submit"
            disabled={sendMutation.isPending || (!messageText.trim() && selectedFiles.length === 0)}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sendMutation.isPending ? 'Отправка...' : 'Отправить'}
          </button>
        </form>
      </div>
    </div>
  )
}

