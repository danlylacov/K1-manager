import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminUsersApi, AdminUser, AdminUserCreate, AdminUserUpdate } from '../services/usersApi';
import { useState } from 'react';

export default function AdminUsersPage() {
  const queryClient = useQueryClient();
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<AdminUserCreate>({
    username: '',
    password: '',
    role: 'manager',
  });
  const [editFormData, setEditFormData] = useState<AdminUserUpdate>({});

  const { data: users, isLoading } = useQuery({
    queryKey: ['adminUsers'],
    queryFn: adminUsersApi.getAll,
  });

  const createMutation = useMutation({
    mutationFn: adminUsersApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      setIsCreating(false);
      setFormData({ username: '', password: '', role: 'manager' });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: AdminUserUpdate }) =>
      adminUsersApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      setEditingId(null);
      setEditFormData({});
    },
  });

  const deleteMutation = useMutation({
    mutationFn: adminUsersApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  const handleUpdate = (id: number) => {
    updateMutation.mutate({ id, data: editFormData });
  };

  const handleDelete = (id: number) => {
    if (confirm('Вы уверены, что хотите удалить этого пользователя?')) {
      deleteMutation.mutate(id);
    }
  };

  const startEdit = (user: AdminUser) => {
    setEditingId(user.id);
    setEditFormData({ username: user.username, role: user.role });
  };

  if (isLoading) {
    return <div className="text-center py-8">Загрузка...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-primary-blue">Управление пользователями</h1>
        <button
          onClick={() => setIsCreating(true)}
          className="btn-primary"
        >
          + Добавить пользователя
        </button>
      </div>

      {isCreating && (
        <div className="card mb-6">
          <h2 className="text-xl font-semibold mb-4">Создать пользователя</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Логин</label>
              <input
                type="text"
                required
                className="input-field"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Пароль</label>
              <input
                type="password"
                required
                className="input-field"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Роль</label>
              <select
                className="input-field"
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              >
                <option value="manager">Manager</option>
                <option value="admin">Admin</option>
                <option value="dev">Dev</option>
              </select>
            </div>
            <div className="flex space-x-2">
              <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Создание...' : 'Создать'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false);
                  setFormData({ username: '', password: '', role: 'manager' });
                }}
                className="btn-secondary"
              >
                Отмена
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div className="hidden md:block overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Логин</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Роль</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Создан</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Действия</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {users?.map((user) => (
              <tr key={user.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm">{user.id}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {editingId === user.id ? (
                    <input
                      type="text"
                      className="input-field"
                      value={editFormData.username || user.username}
                      onChange={(e) => setEditFormData({ ...editFormData, username: e.target.value })}
                    />
                  ) : (
                    user.username
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {editingId === user.id ? (
                    <select
                      className="input-field"
                      value={editFormData.role || user.role}
                      onChange={(e) => setEditFormData({ ...editFormData, role: e.target.value })}
                    >
                      <option value="manager">Manager</option>
                      <option value="admin">Admin</option>
                      <option value="dev">Dev</option>
                    </select>
                  ) : (
                    <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                      {user.role}
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {new Date(user.created_at).toLocaleDateString('ru-RU')}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {editingId === user.id ? (
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleUpdate(user.id)}
                        className="text-green-600 hover:text-green-800"
                        disabled={updateMutation.isPending}
                      >
                        Сохранить
                      </button>
                      <button
                        onClick={() => {
                          setEditingId(null);
                          setEditFormData({});
                        }}
                        className="text-gray-600 hover:text-gray-800"
                      >
                        Отмена
                      </button>
                    </div>
                  ) : (
                    <div className="flex space-x-2">
                      <button
                        onClick={() => startEdit(user)}
                        className="text-primary-blue hover:text-primary-darkBlue"
                      >
                        Редактировать
                      </button>
                      <button
                        onClick={() => handleDelete(user.id)}
                        className="text-red-600 hover:text-red-800"
                        disabled={deleteMutation.isPending}
                      >
                        Удалить
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
        
        {/* Mobile cards */}
        <div className="md:hidden space-y-4">
          {users?.map((user) => (
            <div key={user.id} className="border rounded-lg p-4 space-y-2">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-semibold">{user.username}</p>
                  <p className="text-sm text-gray-600">ID: {user.id}</p>
                </div>
                <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                  {user.role}
                </span>
              </div>
              <p className="text-sm text-gray-600">
                Создан: {new Date(user.created_at).toLocaleDateString('ru-RU')}
              </p>
              {editingId === user.id ? (
                <div className="space-y-2">
                  <input
                    type="text"
                    className="input-field"
                    value={editFormData.username || user.username}
                    onChange={(e) => setEditFormData({ ...editFormData, username: e.target.value })}
                  />
                  <select
                    className="input-field"
                    value={editFormData.role || user.role}
                    onChange={(e) => setEditFormData({ ...editFormData, role: e.target.value })}
                  >
                    <option value="manager">Manager</option>
                    <option value="admin">Admin</option>
                    <option value="dev">Dev</option>
                  </select>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleUpdate(user.id)}
                      className="flex-1 btn-primary text-sm"
                      disabled={updateMutation.isPending}
                    >
                      Сохранить
                    </button>
                    <button
                      onClick={() => {
                        setEditingId(null);
                        setEditFormData({});
                      }}
                      className="flex-1 btn-secondary text-sm"
                    >
                      Отмена
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex space-x-2">
                  <button
                    onClick={() => startEdit(user)}
                    className="flex-1 btn-primary text-sm"
                  >
                    Редактировать
                  </button>
                  <button
                    onClick={() => handleDelete(user.id)}
                    className="flex-1 btn-secondary text-sm text-red-600"
                    disabled={deleteMutation.isPending}
                  >
                    Удалить
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

