import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const rootElement = document.getElementById('root');

if (!rootElement) {
  document.body.innerHTML = '<h1 style="color: red;">Error: Root element not found!</h1>';
} else {
  createRoot(rootElement).render(<App />);
}