<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const { getUsers, createUser, deleteUser, isLoading, error } = useAdminApi()

const users = ref<any[]>([])
const searchTerm = ref('')
const showCreateUserModal = ref(false)

// Create user form
const newUser = ref({
  email: '',
  password: '',
  workspace_name: ''
})

async function loadUsers() {
  try {
    const response = await getUsers()
    users.value = response.users
  } catch (err) {
    console.error('Failed to load users:', err)
  }
}

async function handleCreateUser() {
  try {
    await createUser(
      newUser.value.email, 
      newUser.value.password, 
      newUser.value.workspace_name || undefined
    )
    showCreateUserModal.value = false
    newUser.value = { email: '', password: '', workspace_name: '' }
    await loadUsers()
  } catch (err) {
    console.error('Failed to create user:', err)
  }
}

const filteredUsers = computed(() => {
  if (!searchTerm.value) return users.value
  return users.value.filter(user => 
    user.email.toLowerCase().includes(searchTerm.value.toLowerCase())
  )
})

async function handleDeleteUser(userId: string, userEmail: string) {
  if (confirm(`Are you sure you want to delete user "${userEmail}"? This action cannot be undone and will also delete all workspaces owned by this user.`)) {
    try {
      await deleteUser(userId)
      await loadUsers()
    } catch (err) {
      console.error('Failed to delete user:', err)
    }
  }
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString()
}

onMounted(() => {
  loadUsers()
})
</script>

<template>
  <div>
    <div class="sm:flex sm:items-center">
      <div class="sm:flex-auto">
        <h2 class="text-2xl font-bold text-gray-900">User Management</h2>
        <p class="mt-2 text-sm text-gray-700">
          Manage all user accounts in the system
        </p>
      </div>
      <div class="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
        <button
          @click="showCreateUserModal = true"
          class="inline-flex items-center justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          Create User
        </button>
      </div>
    </div>

    <!-- Search -->
    <div class="mt-6">
      <div class="max-w-md">
        <label for="search" class="sr-only">Search users</label>
        <input
          id="search"
          v-model="searchTerm"
          type="text"
          placeholder="Search users by email..."
          class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
        />
      </div>
    </div>

    <!-- Error message -->
    <div v-if="error" class="mt-4 rounded-md bg-red-50 p-4">
      <div class="flex">
        <div class="ml-3">
          <h3 class="text-sm font-medium text-red-800">
            {{ error }}
          </h3>
        </div>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="mt-6 text-center">
      <div class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent"></div>
      <p class="mt-2 text-sm text-gray-600">Loading users...</p>
    </div>

    <!-- Users table -->
    <div v-else-if="filteredUsers.length > 0" class="mt-6 flow-root">
      <div class="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
        <div class="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
          <div class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
            <table class="min-w-full divide-y divide-gray-300">
              <thead class="bg-gray-50">
                <tr>
                  <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Updated
                  </th>
                  <th scope="col" class="relative px-6 py-3">
                    <span class="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr v-for="user in filteredUsers" :key="user.id">
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {{ user.email }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <span
                      class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                      :class="{
                        'bg-green-100 text-green-800': user.is_active,
                        'bg-red-100 text-red-800': !user.is_active
                      }"
                    >
                      {{ user.is_active ? 'Active' : 'Inactive' }}
                    </span>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {{ formatDate(user.created_at) }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {{ formatDate(user.updated_at) }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div class="flex justify-end space-x-2">
                      <button class="text-indigo-600 hover:text-indigo-900">
                        View Details
                      </button>
                      <button 
                        @click="handleDeleteUser(user.id, user.email)"
                        class="text-red-600 hover:text-red-900"
                        :disabled="isLoading"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!isLoading" class="mt-6 text-center">
      <svg
        class="mx-auto h-12 w-12 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"
        />
      </svg>
      <h3 class="mt-2 text-sm font-medium text-gray-900">No users found</h3>
      <p class="mt-1 text-sm text-gray-500">
        {{ searchTerm ? 'Try adjusting your search criteria.' : 'No users have been created yet.' }}
      </p>
    </div>

    <!-- Create User Modal -->
    <div v-if="showCreateUserModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Create New User</h3>
          <form @submit.prevent="handleCreateUser">
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
              <input
                v-model="newUser.email"
                type="email"
                required
                class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                placeholder="user@example.com"
              />
            </div>
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-2">Password</label>
              <input
                v-model="newUser.password"
                type="password"
                required
                class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                placeholder="Enter secure password"
              />
            </div>
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-2">Initial Workspace (Optional)</label>
              <input
                v-model="newUser.workspace_name"
                type="text"
                class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                placeholder="My Workspace"
              />
              <p class="mt-1 text-sm text-gray-500">Leave empty to create user without workspace</p>
            </div>
            <div class="flex justify-end space-x-3">
              <button
                type="button"
                @click="showCreateUserModal = false"
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="isLoading"
                class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {{ isLoading ? 'Creating...' : 'Create User' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>