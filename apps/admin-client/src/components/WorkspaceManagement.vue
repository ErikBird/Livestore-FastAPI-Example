<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAdminApi } from '../composables/useAdminApi'

const { 
  getWorkspaces, 
  getWorkspaceDetails, 
  createWorkspace, 
  deleteWorkspace,
  addWorkspaceMember, 
  removeWorkspaceMember,
  isLoading, 
  error 
} = useAdminApi()

const workspaces = ref<any[]>([])
const selectedWorkspace = ref<any>(null)
const showCreateModal = ref(false)
const showMemberModal = ref(false)

// Create workspace form
const newWorkspace = ref({
  name: '',
  owner_email: ''
})

// Add member form
const newMember = ref({
  user_email: '',
  role: 'member'
})

async function loadWorkspaces() {
  try {
    const response = await getWorkspaces()
    workspaces.value = response.workspaces
  } catch (err) {
    console.error('Failed to load workspaces:', err)
  }
}

async function viewWorkspaceDetails(workspaceId: string) {
  try {
    const details = await getWorkspaceDetails(workspaceId)
    selectedWorkspace.value = details
  } catch (err) {
    console.error('Failed to load workspace details:', err)
  }
}

async function handleCreateWorkspace() {
  try {
    await createWorkspace(newWorkspace.value.name, newWorkspace.value.owner_email)
    showCreateModal.value = false
    newWorkspace.value = { name: '', owner_email: '' }
    await loadWorkspaces()
  } catch (err) {
    console.error('Failed to create workspace:', err)
  }
}

async function handleAddMember() {
  if (!selectedWorkspace.value) return
  
  try {
    await addWorkspaceMember(
      selectedWorkspace.value.workspace.id,
      newMember.value.user_email,
      newMember.value.role
    )
    showMemberModal.value = false
    newMember.value = { user_email: '', role: 'member' }
    await viewWorkspaceDetails(selectedWorkspace.value.workspace.id)
  } catch (err) {
    console.error('Failed to add member:', err)
  }
}

async function handleRemoveMember(userId: string) {
  if (!selectedWorkspace.value) return
  
  if (confirm('Are you sure you want to remove this member?')) {
    try {
      await removeWorkspaceMember(selectedWorkspace.value.workspace.id, userId)
      await viewWorkspaceDetails(selectedWorkspace.value.workspace.id)
    } catch (err) {
      console.error('Failed to remove member:', err)
    }
  }
}

async function handleDeleteWorkspace() {
  if (!selectedWorkspace.value) return
  
  if (confirm(`Are you sure you want to delete workspace "${selectedWorkspace.value.workspace.name}"? This action cannot be undone and will remove all members.`)) {
    try {
      await deleteWorkspace(selectedWorkspace.value.workspace.id)
      selectedWorkspace.value = null
      await loadWorkspaces()
    } catch (err) {
      console.error('Failed to delete workspace:', err)
    }
  }
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString()
}

onMounted(() => {
  loadWorkspaces()
})
</script>

<template>
  <div>
    <div class="sm:flex sm:items-center">
      <div class="sm:flex-auto">
        <h2 class="text-2xl font-bold text-gray-900">Workspace Management</h2>
        <p class="mt-2 text-sm text-gray-700">
          Create and manage workspaces and their members
        </p>
      </div>
      <div class="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
        <button
          @click="showCreateModal = true"
          class="inline-flex items-center justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          Create Workspace
        </button>
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

    <!-- Workspaces list -->
    <div v-if="!selectedWorkspace" class="mt-6">
      <div v-if="isLoading" class="text-center">
        <div class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent"></div>
        <p class="mt-2 text-sm text-gray-600">Loading workspaces...</p>
      </div>

      <div v-else-if="workspaces.length > 0" class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="workspace in workspaces"
          :key="workspace.id"
          class="bg-white overflow-hidden shadow rounded-lg hover:shadow-md transition-shadow cursor-pointer"
          @click="viewWorkspaceDetails(workspace.id)"
        >
          <div class="px-4 py-5 sm:p-6">
            <h3 class="text-lg font-medium text-gray-900 mb-2">{{ workspace.name }}</h3>
            <p class="text-sm text-gray-500 mb-1">Database: {{ workspace.database_name }}</p>
            <p class="text-sm text-gray-500">Created: {{ formatDate(workspace.created_at) }}</p>
          </div>
        </div>
      </div>

      <div v-else class="text-center">
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
            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
          />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900">No workspaces</h3>
        <p class="mt-1 text-sm text-gray-500">Get started by creating a new workspace.</p>
      </div>
    </div>

    <!-- Workspace details -->
    <div v-if="selectedWorkspace" class="mt-6">
      <div class="mb-4">
        <button
          @click="selectedWorkspace = null"
          class="inline-flex items-center text-sm text-indigo-600 hover:text-indigo-500"
        >
          ← Back to workspaces
        </button>
      </div>

      <div class="bg-white shadow overflow-hidden sm:rounded-lg">
        <div class="px-4 py-5 sm:px-6 flex justify-between items-center">
          <div>
            <h3 class="text-lg leading-6 font-medium text-gray-900">
              {{ selectedWorkspace.workspace.name }}
            </h3>
            <p class="mt-1 max-w-2xl text-sm text-gray-500">
              Workspace details and member management
            </p>
          </div>
          <div class="flex space-x-2">
            <button
              @click="showMemberModal = true"
              class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200"
            >
              Add Member
            </button>
            <button
              @click="handleDeleteWorkspace"
              :disabled="isLoading"
              class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200 disabled:opacity-50"
            >
              Delete Workspace
            </button>
          </div>
        </div>
        
        <div class="border-t border-gray-200">
          <dl>
            <div class="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt class="text-sm font-medium text-gray-500">Database Name</dt>
              <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {{ selectedWorkspace.workspace.database_name }}
              </dd>
            </div>
            <div class="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt class="text-sm font-medium text-gray-500">Created</dt>
              <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {{ formatDate(selectedWorkspace.workspace.created_at) }}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      <!-- Members table -->
      <div class="mt-6">
        <h4 class="text-lg font-medium text-gray-900 mb-4">Members ({{ selectedWorkspace.members.length }})</h4>
        
        <div v-if="selectedWorkspace.members.length > 0" class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
          <table class="min-w-full divide-y divide-gray-300">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Joined
                </th>
                <th class="relative px-6 py-3">
                  <span class="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="member in selectedWorkspace.members" :key="member.user_id">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {{ member.email }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span
                    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                    :class="{
                      'bg-purple-100 text-purple-800': member.role === 'admin',
                      'bg-blue-100 text-blue-800': member.role === 'member'
                    }"
                  >
                    {{ member.role }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span
                    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                    :class="{
                      'bg-green-100 text-green-800': member.is_active,
                      'bg-red-100 text-red-800': !member.is_active
                    }"
                  >
                    {{ member.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {{ formatDate(member.joined_at) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button
                    v-if="member.user_id !== selectedWorkspace.workspace.owner_id"
                    @click="handleRemoveMember(member.user_id)"
                    class="text-red-600 hover:text-red-900"
                  >
                    Remove
                  </button>
                  <span v-else class="text-gray-400">Owner</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <div v-else class="text-center py-12">
          <p class="text-sm text-gray-500">No members found</p>
        </div>
      </div>
    </div>

    <!-- Create Workspace Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Create New Workspace</h3>
          <form @submit.prevent="handleCreateWorkspace">
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-2">Workspace Name</label>
              <input
                v-model="newWorkspace.name"
                type="text"
                required
                class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                placeholder="My Workspace"
              />
            </div>
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-2">Owner Email</label>
              <input
                v-model="newWorkspace.owner_email"
                type="email"
                required
                class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                placeholder="user@example.com"
              />
            </div>
            <div class="flex justify-end space-x-3">
              <button
                type="button"
                @click="showCreateModal = false"
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="isLoading"
                class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {{ isLoading ? 'Creating...' : 'Create' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Add Member Modal -->
    <div v-if="showMemberModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Add Member</h3>
          <form @submit.prevent="handleAddMember">
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-2">User Email</label>
              <input
                v-model="newMember.user_email"
                type="email"
                required
                class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                placeholder="user@example.com"
              />
            </div>
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-2">Role</label>
              <select
                v-model="newMember.role"
                class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div class="flex justify-end space-x-3">
              <button
                type="button"
                @click="showMemberModal = false"
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="isLoading"
                class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {{ isLoading ? 'Adding...' : 'Add Member' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>