<script setup lang="ts">
const emit = defineEmits<{
  'switch-to-login': []
}>()
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div class="text-center">
        <div class="mx-auto h-24 w-24 flex items-center justify-center rounded-full bg-red-100">
          <svg class="h-12 w-12 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Registration Disabled
        </h2>
        <p class="mt-4 text-sm text-gray-600">
          Self-registration is not available. Please contact your system administrator to create an account.
        </p>
      </div>
      
      <div class="text-center">
        <button
          type="button"
          @click="emit('switch-to-login')"
          class="text-indigo-600 hover:text-indigo-500 font-medium"
        >
          Back to Sign In
        </button>
      </div>
    </div>
  </div>
</template>