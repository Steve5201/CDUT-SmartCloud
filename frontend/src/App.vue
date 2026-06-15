<!-- src/App.vue -->
<template>
  <!-- <router-view> 就是舞台。当访问 /login 时，它显示登录页；访问 /chat 时，显示聊天页 -->
  <router-view></router-view>
</template>

<script setup>
// 这个文件现在变得极简，所有的脏活全下放给具体的页面(views)去了
</script>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100vh; /* 撑满屏幕高度 */
  background-color: #f0f2f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif;
}
</style>