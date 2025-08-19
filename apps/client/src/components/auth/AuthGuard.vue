<script setup lang="ts">
import { useAuth } from '../../composables/useAuth'
import LoginForm from './LoginForm.vue'

const { isAuthenticated } = useAuth()

function handleLoginSuccess() {
  // Emit event or reload the page if needed
  window.location.reload()
}
</script>

<template>
  <div v-if="!isAuthenticated">
    <LoginForm @login-success="handleLoginSuccess" />
  </div>
  <div v-else>
    <slot />
  </div>
</template>