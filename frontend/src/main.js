/** 运行时必需。Vue 应用入口：挂载 App、注册路由与全局样式。 */
import { createApp } from 'vue';
import App from './App.vue';
import router from './router/index.js';
import 'driver.js/dist/driver.css';
import './styles/main.css';

createApp(App).use(router).mount('#app');
