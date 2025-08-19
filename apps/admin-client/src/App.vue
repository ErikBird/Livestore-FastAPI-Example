<script setup lang="ts">
import { ref } from 'vue'
import { useAdminAuth } from './composables/useAdminAuth'
import AdminLogin from './components/AdminLogin.vue'
import AdminDashboard from './components/AdminDashboard.vue'

const { isAuthenticated } = useAdminAuth()

function handleLoginSuccess() {
  // The reactive state will automatically update the UI
}
</script>

<template>
  <div id="app">
    <AdminLogin 
      v-if="!isAuthenticated" 
      @login-success="handleLoginSuccess" 
    />
    <AdminDashboard v-else />
  </div>
</template>
