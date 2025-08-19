<script setup lang="ts">
import { queryDb } from '@livestore/livestore'
import { events, tables } from '../livestore/schema'
import { useStore } from 'vue-livestore'

const { store } = useStore()

// Query & subscription
const uiState$ = queryDb(tables.uiState.get(), { label: 'uiState' })

const visibleTodos$ = queryDb(
  (get) => {
    const filter = get(uiState$).filter
    return tables.todos.where({
      deletedAt: null,
      completed: filter === 'all' ? undefined : filter === 'completed'
    })
  },
  { label: 'visibleTodos' },
)

const { newTodoText, filter } = store.useClientDocument(tables.uiState)
const todos = store.useQuery(visibleTodos$)

// Events
const createTodo = () => {
  store.commit(events.todoCreated({ id: crypto.randomUUID(), text: newTodoText.value }))
  newTodoText.value = ''
}

const deleteTodo = (id: string) => {
  store.commit(events.todoDeleted({ id, deletedAt: new Date() }))
}

const toggleCompleted = (id: string) => {
  if (todos.value.find((todo) => todo.id === id)?.completed) {
    store.commit(events.todoUncompleted({ id }))
  } else {
    store.commit(events.todoCompleted({ id }))
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
    <div class="max-w-2xl mx-auto">
      <h1 class="text-4xl font-bold text-gray-800 mb-8 text-center">Todo List</h1>
      
      <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
        <div class="flex gap-2 mb-4">
          <input
            type="text"
            v-model="newTodoText"
            @keyup.enter="createTodo"
            placeholder="What needs to be done?"
            class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button 
            @click="createTodo"
            class="px-6 py-2 bg-blue-500 text-white font-medium rounded-lg hover:bg-blue-600 transition-colors duration-200"
          >
            Add Todo
          </button>
        </div>
        
        <div class="flex gap-2 justify-center">
          <button
            @click="filter = 'all'"
            :class="[
              'px-4 py-2 rounded-lg font-medium transition-all duration-200',
              filter === 'all' 
                ? 'bg-gray-800 text-white shadow-md' 
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            ]"
          >
            All
          </button>
          <button
            @click="filter = 'active'"
            :class="[
              'px-4 py-2 rounded-lg font-medium transition-all duration-200',
              filter === 'active' 
                ? 'bg-gray-800 text-white shadow-md' 
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            ]"
          >
            Active
          </button>
          <button
            @click="filter = 'completed'"
            :class="[
              'px-4 py-2 rounded-lg font-medium transition-all duration-200',
              filter === 'completed' 
                ? 'bg-gray-800 text-white shadow-md' 
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            ]"
          >
            Completed
          </button>
        </div>
      </div>
      
      <div class="space-y-2">
        <div
          v-for="todo in todos"
          :key="todo.id"
          class="bg-white rounded-lg shadow p-4 flex items-center justify-between hover:shadow-md transition-shadow duration-200"
        >
          <span 
            :class="[
              'text-lg',
              todo.completed ? 'line-through text-gray-400' : 'text-gray-700'
            ]"
          >
            {{ todo.text }}
          </span>
          <div class="flex gap-2">
            <button 
              @click="toggleCompleted(todo.id)"
              :class="[
                'px-3 py-1 rounded font-medium transition-colors duration-200',
                todo.completed 
                  ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                  : 'bg-green-100 text-green-700 hover:bg-green-200'
              ]"
            >
              {{ todo.completed ? 'Undo' : 'Complete' }}
            </button>
            <button 
              @click="deleteTodo(todo.id)"
              class="px-3 py-1 bg-red-100 text-red-700 rounded font-medium hover:bg-red-200 transition-colors duration-200"
            >
              Delete
            </button>
          </div>
        </div>
        
        <div v-if="todos.length === 0" class="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          <p class="text-lg">No todos to display</p>
          <p class="text-sm mt-2">Add a new todo to get started!</p>
        </div>
      </div>
    </div>
  </div>
</template>

