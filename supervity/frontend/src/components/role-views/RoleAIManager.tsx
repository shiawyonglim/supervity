'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Icons } from '@/components/ui/icons'
import { Badge } from '@/components/ui/badge'
import { ChatInput } from '@/components/ai/ChatInput'
import { ChatMessage } from '@/components/ai/ChatMessage'
import dynamic from 'next/dynamic'
import type { AppRole } from '@/context/RoleContext'
import { ROLE_META } from '@/context/RoleContext'

const KnowledgeBasePanel = dynamic(
  () => import('@/components/ai/manager/KnowledgeBasePanel').then((m) => m.KnowledgeBasePanel),
  { ssr: false, loading: () => <div className='p-8 text-center text-muted-foreground'>Loading Knowledge Base...</div> }
)

interface ChatMessageState {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isLoading?: boolean
  toolCalls?: Array<{ id: string; name: string; args: Record<string, unknown>; result?: unknown }>
}

interface RemoteSession {
  id: number
  role: string
  name: string
  updated_at: string
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
}

const marketingPrompts = [
  'Suggest a marketing strategy for enterprise SaaS leads.',
  'What content converts pricing page visitors best?',
  'Recommend a follow-up cadence for MQLs.',
  'How should we nurture cold leads in GDPR regions?',
  'Which channels should we prioritize this quarter?',
]

const welcomeMessage: ChatMessageState = {
  id: 'welcome',
  role: 'assistant',
  content: `Hello, I'm your AI Manager. Ask me about marketing strategies, lead follow-up, or sales enablement.`,
  timestamp: new Date(),
}

export function RoleAIManager({ role }: { role: AppRole }) {
  const meta = ROLE_META[role]
  const isCro = role === 'cro'

  const [messages, setMessages] = useState<ChatMessageState[]>([welcomeMessage])
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null)
  const [view, setView] = useState<'chat' | 'knowledge'>('chat')
  const [sessions, setSessions] = useState<RemoteSession[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true)
    try {
      const qs = isCro ? '' : `?role=${role}`
      const res = await apiClient.get<{ sessions: RemoteSession[] }>(`/api/chat/sessions${qs}`)
      setSessions(res.sessions || [])
    } catch (err) {
      console.error('Failed to load chat sessions:', err)
    } finally {
      setSessionsLoading(false)
    }
  }, [role, isCro])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const persistMessages = useCallback(async (toSave: ChatMessageState[], sessionId?: number | null) => {
    if (toSave.length === 0) return
    setSaving(true)
    try {
      if (sessionId) {
        // Append each new message to the existing session.
        for (const m of toSave) {
          await apiClient.post(`/api/chat/sessions/${sessionId}/message`, {
            role: m.role,
            content: m.content,
            tool_calls: m.toolCalls || [],
          })
        }
      } else {
        // First time this conversation is being saved.
        const name = toSave[0]?.content?.slice(0, 60) || 'AI Manager chat'
        const res = await apiClient.post<{ id: number }>('/api/chat/sessions', {
          role,
          name: `${meta.label} — ${name}`,
          messages: toSave.map((m) => ({
            role: m.role,
            content: m.content,
            tool_calls: m.toolCalls || [],
          })),
        })
        setCurrentSessionId(res.id)
      }
      await loadSessions()
    } catch (err) {
      console.error('Failed to save chat session:', err)
    } finally {
      setSaving(false)
    }
  }, [role, meta.label, loadSessions])

  const handleSend = useCallback(async (content: string) => {
    const userMessage: ChatMessageState = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    }

    const priorMessages = messages
    const isFirstExchange = !currentSessionId && priorMessages.length === 1

    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    // If we already have a session, persist the new user message immediately.
    if (currentSessionId) {
      await persistMessages([userMessage], currentSessionId)
    }

    const loadingMessage: ChatMessageState = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    }
    setMessages((prev) => [...prev, loadingMessage])

    try {
      const res = await apiClient.post<{ response: string; tool_calls?: ChatMessageState['toolCalls'] }>('/api/ai/chat', {
        message: content,
        history: priorMessages.filter((m) => !m.isLoading).map((m) => ({ role: m.role, content: m.content })),
        context: { page: '/ai/manager', role, topic: 'marketing' },
      })

      const assistantMessage: ChatMessageState = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: res.response || 'I am not sure how to answer that.',
        timestamp: new Date(),
        toolCalls: res.tool_calls,
      }

      setMessages((prev) => [
        ...prev.filter((m) => !m.isLoading),
        assistantMessage,
      ])

      // Persist the full first exchange, or just the assistant reply.
      if (isFirstExchange) {
        await persistMessages([userMessage, assistantMessage], null)
      } else if (currentSessionId) {
        await persistMessages([assistantMessage], currentSessionId)
      }
    } catch (err) {
      console.error('AI Manager chat failed:', err)
      setMessages((prev) => [
        ...prev.filter((m) => !m.isLoading),
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }, [messages, currentSessionId, role, persistMessages])

  const loadSession = async (id: number) => {
    try {
      const res = await apiClient.get<{
        id: number
        role: string
        name: string
        messages: Array<{
          id: number
          role: 'user' | 'assistant'
          content: string
          timestamp: string
          tool_calls?: ChatMessageState['toolCalls']
        }>
      }>(`/api/chat/sessions/${id}`)

      const loaded: ChatMessageState[] = res.messages.map((m) => ({
        id: String(m.id),
        role: m.role,
        content: m.content,
        timestamp: new Date(m.timestamp),
        toolCalls: m.tool_calls,
      }))

      setMessages(loaded)
      setCurrentSessionId(res.id)
    } catch (err) {
      console.error('Failed to load session:', err)
    }
  }

  const startNewChat = () => {
    setMessages([welcomeMessage])
    setCurrentSessionId(null)
  }

  return (
    <motion.div className='space-y-6' variants={containerVariants} initial='hidden' animate='visible'>
      <motion.div variants={itemVariants} className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
        <div>
          <h1 className='text-display-3 font-bold tracking-tight text-brand-navy'>AI Manager</h1>
          <p className='mt-2 text-lg text-muted-foreground'>
            {isCro
              ? 'Marketing strategy chat and team session reviews.'
              : 'Connected to the knowledge base for marketing strategy and sales guidance.'}
          </p>
        </div>
        <div className='flex items-center gap-2'>
          <Button variant='outline' size='sm' onClick={startNewChat}>
            <Icons.plus className='mr-1.5 h-4 w-4' />
            New Chat
          </Button>
          <Badge className={cn('rounded-md border px-2.5 py-1 text-xs font-bold uppercase tracking-wide', meta.color)}>
            {meta.label}
          </Badge>
        </div>
      </motion.div>

      <div className='grid gap-6 lg:grid-cols-4'>
        {/* Left sidebar */}
        <motion.div variants={itemVariants} className='lg:col-span-1 space-y-4'>
          <Card>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                <Icons.grid className='h-5 w-5 text-brand-cornflower' />
                AI Manager
              </CardTitle>
              <CardDescription>Switch between chat and knowledge base.</CardDescription>
            </CardHeader>
            <CardContent className='space-y-2'>
              <button
                onClick={() => setView('chat')}
                className={cn(
                  'flex w-full items-center gap-2 rounded-lg border p-3 text-left text-sm transition-colors',
                  view === 'chat'
                    ? 'border-brand-cornflower bg-brand-cornflower/5 text-brand-navy'
                    : 'border-border/50 bg-white text-foreground hover:border-brand-cornflower/50 hover:bg-brand-cornflower/5'
                )}
              >
                <Icons.messageSquare className='h-4 w-4' />
                Chat
              </button>
              <button
                onClick={() => setView('knowledge')}
                className={cn(
                  'flex w-full items-center gap-2 rounded-lg border p-3 text-left text-sm transition-colors',
                  view === 'knowledge'
                    ? 'border-brand-cornflower bg-brand-cornflower/5 text-brand-navy'
                    : 'border-border/50 bg-white text-foreground hover:border-brand-cornflower/50 hover:bg-brand-cornflower/5'
                )}
              >
                <Icons.brain className='h-4 w-4' />
                Knowledge Base
              </button>
            </CardContent>
          </Card>

          {view === 'chat' && (
            <Card>
              <CardHeader>
                <CardTitle className='flex items-center gap-2'>
                  <Icons.lightbulb className='h-5 w-5 text-brand-cornflower' />
                  Marketing Prompts
                </CardTitle>
                <CardDescription>Tap a starter question.</CardDescription>
              </CardHeader>
              <CardContent className='space-y-2'>
                {marketingPrompts.map((p) => (
                  <button
                    key={p}
                    onClick={() => handleSend(p)}
                    className='w-full rounded-lg border border-border/50 bg-white p-3 text-left text-sm text-foreground transition-colors hover:border-brand-cornflower/50 hover:bg-brand-cornflower/5'
                  >
                    {p}
                  </button>
                ))}
              </CardContent>
            </Card>
          )}

          <Card className='h-full'>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                <Icons.clock className='h-5 w-5 text-brand-cornflower' />
                {isCro ? 'Team Chat History' : 'My Chat History'}
              </CardTitle>
              <CardDescription>
                {isCro ? 'Review conversations from other sales roles.' : 'Jump back to a recent chat.'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {sessionsLoading ? (
                <div className='flex justify-center p-4'>
                  <Icons.loader className='h-5 w-5 animate-spin text-muted-foreground' />
                </div>
              ) : sessions.length === 0 ? (
                <p className='text-center text-sm text-muted-foreground'>No saved sessions yet.</p>
              ) : (
                <div className='space-y-2'>
                  {sessions.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => { setView('chat'); loadSession(s.id) }}
                      className={cn(
                        'w-full rounded-lg border p-3 text-left text-sm transition-colors',
                        currentSessionId === s.id && view === 'chat'
                          ? 'border-brand-cornflower bg-brand-cornflower/5 text-brand-navy'
                          : 'border-border/50 bg-white text-foreground hover:border-brand-cornflower/50 hover:bg-brand-cornflower/5'
                      )}
                    >
                      <p className='line-clamp-1 font-medium'>{s.name}</p>
                      <div className='mt-1 flex items-center gap-2 text-[10px] text-muted-foreground uppercase'>
                        <Badge variant='outline' className='text-[10px]'>{s.role}</Badge>
                        <span>{new Date(s.updated_at).toLocaleDateString()}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Right panel */}
        <motion.div variants={itemVariants} className='lg:col-span-3'>
          {view === 'knowledge' ? (
            <Card className='h-[70vh] overflow-y-auto p-5'>
              <KnowledgeBasePanel />
            </Card>
          ) : (
            <Card className='flex h-[70vh] flex-col'>
              <CardHeader className='border-b'>
                <div className='flex items-center justify-between'>
                  <div>
                    <CardTitle className='flex items-center gap-2'>
                      <Icons.sparkles className='h-5 w-5 text-brand-purple' />
                      Chat
                      {currentSessionId && isCro && (
                        <Badge variant='secondary' className='text-[10px]'>Reviewing session</Badge>
                      )}
                    </CardTitle>
                    <CardDescription>
                      {isCro
                        ? 'Open a team session to review or add a CRO recommendation.'
                        : 'Ask about marketing strategies, sales playbooks, or next-best actions.'}
                    </CardDescription>
                  </div>
                  {saving && <Icons.loader className='h-4 w-4 animate-spin text-muted-foreground' />}
                </div>
              </CardHeader>
              <CardContent className='flex flex-1 flex-col overflow-hidden p-0'>
                <div className='flex-1 space-y-4 overflow-y-auto p-4'>
                  {messages.map((msg) => (
                    <ChatMessage
                      key={msg.id}
                      message={msg}
                      userName={msg.role === 'user' ? 'You' : 'AutoPilot'}
                    />
                  ))}
                  <div ref={messagesEndRef} />
                </div>
                <div className='border-t bg-gradient-to-t from-gray-50/80 to-transparent p-4'>
                  <ChatInput
                    onSend={handleSend}
                    isLoading={isLoading}
                    placeholder={
                      isCro && currentSessionId
                        ? 'Add a CRO recommendation...'
                        : 'Ask about marketing strategies...'
                    }
                  />
                </div>
              </CardContent>
            </Card>
          )}
        </motion.div>
      </div>
    </motion.div>
  )
}
