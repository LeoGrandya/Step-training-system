# Frontend (Vue 3 + Vite)

AI-Sport Lab 前端源码，构建产物输出到 `../web_1/static/spa/`。

## 开发

```powershell
cd D:\app\web_html\pose3d_project_3.0\frontend
npm.cmd install
npm.cmd run dev
```

Vite 开发服务器：`http://127.0.0.1:5173`，`/api` 代理到 Flask `http://127.0.0.1:5000`。

同时启动 Flask（在 `web_1/` 目录）：

```powershell
cd D:\app\web_html\pose3d_project_3.0\web_1
python v1.py
```

## 生产构建

```powershell
cd D:\app\web_html\pose3d_project_3.0\frontend
npm.cmd run build
```

然后只启动 Flask，访问 `http://127.0.0.1:5000/`。

## 目录

- `src/` — Vue 路由、训练页、登录页
- `public/videos/footwork/` — 步伐示范视频（可选）
- 静态 HTML 页面在 `../site/`，由 Flask 的 `/legacy-html/` 与 `/assets/` 提供

## 测试

```powershell
npm.cmd test
npm.cmd run build
```
