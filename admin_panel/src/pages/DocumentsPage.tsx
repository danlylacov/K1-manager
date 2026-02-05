import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { documentsApi } from '../services/documentsApi'
import { useState } from 'react'

export default function DocumentsPage() {
  const queryClient = useQueryClient()
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [replaceAll, setReplaceAll] = useState(true)
  const [updateDoc, setUpdateDoc] = useState<string | null>(null)
  const [updateFile, setUpdateFile] = useState<File | null>(null)
  
  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: documentsApi.getAll,
    staleTime: 60000, // Кэшировать на 1 минуту
    gcTime: 300000, // Хранить в кэше 5 минут
  })
  
  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!uploadFile) throw new Error('No file selected')
      await documentsApi.upload(uploadFile, replaceAll)
    },
    onSuccess: () => {
      setUploadFile(null)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })
  
  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!updateDoc || !updateFile) throw new Error('Missing data')
      await documentsApi.update(updateDoc, updateFile)
    },
    onSuccess: () => {
      setUpdateDoc(null)
      setUpdateFile(null)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })
  
  const deleteMutation = useMutation({
    mutationFn: documentsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })
  
  if (isLoading) {
    return <div className="text-center py-8">Загрузка документов...</div>
  }
  
  return (
    <div>
      <h1 className="text-3xl font-bold text-primary-blue mb-6">Управление документами</h1>
      
      <div className="card mb-6">
        <h2 className="text-xl font-semibold mb-4">Статистика</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-primary-lightBlue p-4 rounded-lg text-white">
            <p className="text-sm">Всего документов</p>
            <p className="text-2xl font-bold">{documents?.total_documents || 0}</p>
          </div>
          <div className="bg-primary-yellow p-4 rounded-lg">
            <p className="text-sm text-gray-900">Всего чанков</p>
            <p className="text-2xl font-bold text-gray-900">{documents?.total_chunks || 0}</p>
          </div>
        </div>
      </div>
      
      <div className="card mb-6">
        <h2 className="text-xl font-semibold mb-4">Загрузить новый документ</h2>
        <div className="space-y-4">
          <input
            type="file"
            onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
            className="input-field"
          />
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={replaceAll}
              onChange={(e) => setReplaceAll(e.target.checked)}
            />
            <span>Заменить все существующие документы</span>
          </label>
          <button
            onClick={() => uploadMutation.mutate()}
            disabled={!uploadFile || uploadMutation.isPending}
            className="btn-primary disabled:opacity-50"
          >
            {uploadMutation.isPending ? 'Загрузка...' : 'Загрузить'}
          </button>
        </div>
      </div>
      
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Список документов</h2>
        <div className="space-y-4">
          {documents?.documents.map((doc) => (
            <div key={doc.document} className="border p-4 rounded-lg flex justify-between items-center">
              <div>
                <p className="font-medium">{doc.document}</p>
                <p className="text-sm text-gray-600">Чанков: {doc.chunks}</p>
              </div>
              <div className="space-x-2">
                {updateDoc === doc.document ? (
                  <>
                    <input
                      type="file"
                      onChange={(e) => setUpdateFile(e.target.files?.[0] || null)}
                      className="input-field"
                    />
                    <button
                      onClick={() => updateMutation.mutate()}
                      disabled={!updateFile || updateMutation.isPending}
                      className="btn-secondary text-sm"
                    >
                      Сохранить
                    </button>
                    <button
                      onClick={() => {
                        setUpdateDoc(null)
                        setUpdateFile(null)
                      }}
                      className="btn-primary text-sm"
                    >
                      Отмена
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => setUpdateDoc(doc.document)}
                      className="btn-secondary text-sm"
                    >
                      Обновить
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Удалить документ ${doc.document}?`)) {
                          deleteMutation.mutate(doc.document)
                        }
                      }}
                      className="bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 text-sm"
                    >
                      Удалить
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

