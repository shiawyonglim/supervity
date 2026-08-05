'use client'

import { useState, useEffect, useCallback } from 'react'

import { motion } from 'framer-motion'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icons } from '@/components/ui/icons'
import { apiClient } from '@/lib/api-client'
import { Badge } from '@/components/ui/badge'

interface Exception {
  id: number
  type: string
  severity: string
  title: string
  description: string
  prospect_id?: string
  account_name?: string
  context?: any
  ai_recommendation?: string
  ai_confidence?: number
  status: string
  created_at: string
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

export default function WorkbenchPage() {
  const [exceptions, setExceptions] = useState<Exception[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const fetchExceptions = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await apiClient.get<Exception[]>('/api/exceptions')
      setExceptions(data)
    } catch (err) {
      console.error('Failed to load exceptions:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchExceptions()
  }, [fetchExceptions])

  const handleResolve = async (id: number, action: string) => {
    try {
      await apiClient.post(`/api/exceptions/${id}/resolve`, {
        resolution_action: action,
        resolved_by: 'Admin',
        resolution_notes: 'Resolved via Workbench'
      })
      // Optimistic update
      setExceptions(prev => prev.filter(e => e.id !== id))
    } catch (err) {
      console.error('Failed to resolve exception:', err)
    }
  }

  return (
    <motion.div
      className='space-y-8'
      variants={containerVariants}
      initial='hidden'
      animate='visible'
    >
      {/* Header */}
      <motion.div variants={itemVariants}>
        <h1 className='text-display-3 font-bold tracking-tight text-brand-navy'>
          Workbench
        </h1>
        <p className='mt-2 text-lg text-muted-foreground'>
          Access your AI tools and automation workflows.
        </p>
      </motion.div>

      {/* Exception Inbox */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.alertCircle className='h-5 w-5 text-red-500' />
              Exception Inbox
            </CardTitle>
            <CardDescription>
              Review and resolve automated tasks that require human intervention
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center p-8"><Icons.loader className="h-8 w-8 animate-spin text-muted-foreground" /></div>
            ) : exceptions.length === 0 ? (
              <div className="text-center p-8 text-muted-foreground">
                <Icons.checkCircle className="h-12 w-12 mx-auto mb-4 text-emerald-500 opacity-50" />
                <p>No pending exceptions to resolve. Great job!</p>
              </div>
            ) : (
              <div className="space-y-4">
                {exceptions.map(exc => (
                  <div key={exc.id} className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center p-4 border rounded-xl bg-white shadow-sm">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold">{exc.title}</h4>
                        <Badge variant={exc.severity === 'critical' ? 'destructive' : 'secondary'}>
                          {exc.severity}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{exc.description}</p>
                      {exc.ai_recommendation && (
                        <p className="text-sm text-brand-navy font-medium mt-2">
                          <Icons.sparkles className="inline w-3 h-3 mr-1" />
                          AI Suggestion: {exc.ai_recommendation} ({exc.ai_confidence}% confidence)
                        </p>
                      )}
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <Button variant="outline" size="sm" onClick={() => handleResolve(exc.id, 'rejected')}>
                        Reject
                      </Button>
                      <Button variant="default" size="sm" onClick={() => handleResolve(exc.id, 'approved')}>
                        Approve
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Quick Actions */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.zap className='h-5 w-5 text-brand-cornflower' />
              Quick Actions
            </CardTitle>
            <CardDescription>
              Frequently used actions for faster access
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className='flex flex-wrap gap-3'>
              <Button variant='outline' size='sm'>
                <Icons.plus className='mr-2 h-4 w-4' />
                New Task
              </Button>
              <Button variant='outline' size='sm'>
                <Icons.fileText className='mr-2 h-4 w-4' />
                Generate Report
              </Button>
              <Button variant='outline' size='sm'>
                <Icons.mail className='mr-2 h-4 w-4' />
                Send Notification
              </Button>
              <Button variant='outline' size='sm'>
                <Icons.download className='mr-2 h-4 w-4' />
                Export Data
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}
