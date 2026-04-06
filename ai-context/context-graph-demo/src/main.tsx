import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SocketProvider } from '@trustgraph/react-provider'
import { NotificationProvider, NotificationHandler } from '@trustgraph/react-state'
import { toast } from './state'
import './index.css'
import App from './App'

const queryClient = new QueryClient()

const notificationHandler: NotificationHandler = {
  success: (message: string) => toast.success(message),
  error: (message: string) => toast.error(message),
  warning: (message: string) => toast.warning(message),
  info: (message: string) => toast.info(message),
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <NotificationProvider handler={notificationHandler}>
        <SocketProvider user="trustgraph">
          <App />
        </SocketProvider>
      </NotificationProvider>
    </QueryClientProvider>
  </StrictMode>,
)
