'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Icons } from '@/components/ui/icons'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { CreateWithAI } from '@/components/ai/policies/CreateWithAI'
import type { AppRole } from '@/context/RoleContext'
import { ROLE_META } from '@/context/RoleContext'

interface Policy {
  id: string
  name: string
  description: string
  natural_language: string
  policy_type: 'logical' | 'natural_language'
  is_active: boolean
  priority: number
  tags: string[]
}

interface PolicyForm {
  name: string
  description: string
  natural_language: string
  priority: number
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
}

export function RoleAIPolicies({ role }: { role: AppRole }) {
  const meta = ROLE_META[role]
  const [policies, setPolicies] = useState<Policy[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [editPolicy, setEditPolicy] = useState<Policy | null>(null)

  const [form, setForm] = useState<PolicyForm>({
    name: '',
    description: '',
    natural_language: '',
    priority: 50,
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiClient.get<Policy[]>('/api/policies?limit=100')
      setPolicies(data)
    } catch (err) {
      console.error('Policies load failed:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const filtered = policies.filter((p) => {
    const q = search.toLowerCase()
    return (
      p.name.toLowerCase().includes(q) ||
      (p.natural_language || '').toLowerCase().includes(q) ||
      (p.tags || []).some((t) => t.toLowerCase().includes(q))
    )
  })

  const toggle = async (id: string) => {
    try {
      const res = await apiClient.patch<Policy>(`/api/policies/${id}/toggle`)
      setPolicies((prev) => prev.map((p) => (p.id === id ? res : p)))
    } catch (err) {
      console.error('Toggle failed:', err)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this policy?')) return
    try {
      await apiClient.delete(`/api/policies/${id}`)
      setPolicies((prev) => prev.filter((p) => p.id !== id))
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  const handleCreate = async (policy: {
    name: string
    description: string
    naturalLanguage: string
    policyType: 'logical' | 'natural_language'
    dsl: unknown
    refinedInstruction: string | null
    entityName: string | null
    tags: string[]
    priority: number
  }) => {
    await apiClient.post('/api/policies', {
      name: policy.name,
      description: policy.description,
      natural_language: policy.naturalLanguage,
      policy_type: policy.policyType,
      dsl: policy.dsl,
      refined_instruction: policy.refinedInstruction,
      entity_name: policy.entityName,
      tags: policy.tags,
      priority: policy.priority,
      is_active: true,
    })
    setCreateOpen(false)
    await load()
  }

  const openEdit = (p: Policy) => {
    setEditPolicy(p)
    setForm({
      name: p.name,
      description: p.description || '',
      natural_language: p.natural_language || '',
      priority: p.priority,
    })
  }

  const saveEdit = async () => {
    if (!editPolicy) return
    try {
      const res = await apiClient.patch<Policy>(`/api/policies/${editPolicy.id}`, {
        name: form.name,
        description: form.description,
        natural_language: form.natural_language,
        priority: form.priority,
      })
      setPolicies((prev) => prev.map((p) => (p.id === editPolicy.id ? res : p)))
      setEditPolicy(null)
    } catch (err) {
      console.error('Edit failed:', err)
    }
  }

  return (
    <motion.div className='space-y-6' variants={containerVariants} initial='hidden' animate='visible'>
      <motion.div variants={itemVariants} className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
        <div>
          <h1 className='text-display-3 font-bold tracking-tight text-brand-navy'>AI Policies</h1>
          <p className='mt-2 text-lg text-muted-foreground'>
            View, edit, and switch policies on/off.
          </p>
        </div>
        <div className='flex items-center gap-2'>
          <Badge className={cn('rounded-md border px-2.5 py-1 text-xs font-bold uppercase tracking-wide', meta.color)}>
            {meta.label}
          </Badge>
          <Button onClick={() => setCreateOpen(true)}>
            <Icons.plus className='mr-2 h-4 w-4' />
            Create with AI
          </Button>
        </div>
      </motion.div>

      <motion.div variants={itemVariants} className='flex gap-2'>
        <div className='relative flex-1'>
          <Icons.search className='absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground' />
          <input
            type='text'
            placeholder='Search policies...'
            className='h-10 w-full rounded-md border border-input bg-background pl-9 pr-4 text-sm'
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </motion.div>

      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.brain className='h-5 w-5 text-brand-purple' />
              Active Policies
            </CardTitle>
            <CardDescription>
              {filtered.length} of {policies.length} policies shown. Use the toggle to activate or deactivate.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className='flex justify-center p-8'>
                <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
              </div>
            ) : filtered.length === 0 ? (
              <p className='text-center text-muted-foreground'>No policies found.</p>
            ) : (
              <div className='space-y-3'>
                {filtered.map((p) => (
                  <div
                    key={p.id}
                    className={cn(
                      'flex flex-col gap-3 rounded-xl border p-4 transition-colors sm:flex-row sm:items-center sm:justify-between',
                      p.is_active ? 'border-brand-cornflower/30 bg-brand-cornflower/5' : 'border-border/50 bg-muted/20'
                    )}
                  >
                    <div className='min-w-0 flex-1'>
                      <div className='flex items-center gap-2'>
                        <p className='font-medium text-foreground'>{p.name}</p>
                        <Badge className='text-[10px]' variant={p.is_active ? 'default' : 'secondary'}>
                          {p.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </div>
                      <p className='truncate text-xs text-muted-foreground'>{p.natural_language || p.description}</p>
                      <div className='mt-1 flex flex-wrap gap-1'>
                        {(p.tags || []).map((t) => (
                          <span key={t} className='rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground'>
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className='flex items-center gap-2'>
                      <Button variant='ghost' size='sm' onClick={() => openEdit(p)}>
                        <Icons.edit className='mr-1.5 h-4 w-4' />
                        Edit
                      </Button>
                      <Button
                        variant={p.is_active ? 'default' : 'outline'}
                        size='sm'
                        onClick={() => toggle(p.id)}
                      >
                        {p.is_active ? 'On' : 'Off'}
                      </Button>
                      <Button variant='ghost' size='icon-sm' onClick={() => handleDelete(p.id)}>
                        <Icons.trash className='h-4 w-4 text-red-500' />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Create with AI Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className='max-w-3xl max-h-[90vh] overflow-y-auto'>
          <DialogHeader>
            <DialogTitle>Create AI Policy</DialogTitle>
            <DialogDescription>Describe the rule in plain English and let AI turn it into a policy.</DialogDescription>
          </DialogHeader>
          <CreateWithAI onPolicyCreate={handleCreate} onCancel={() => setCreateOpen(false)} />
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editPolicy} onOpenChange={(open) => !open && setEditPolicy(null)}>
        <DialogContent className='sm:max-w-lg'>
          <DialogHeader>
            <DialogTitle>Edit Policy</DialogTitle>
            <DialogDescription>Update the policy details.</DialogDescription>
          </DialogHeader>
          <div className='space-y-4'>
            <div className='space-y-2'>
              <label className='text-sm font-medium'>Name</label>
              <input
                type='text'
                className='h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm'
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className='space-y-2'>
              <label className='text-sm font-medium'>Description</label>
              <textarea
                className='min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm'
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
            <div className='space-y-2'>
              <label className='text-sm font-medium'>Natural Language Rule</label>
              <textarea
                className='min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm'
                value={form.natural_language}
                onChange={(e) => setForm({ ...form, natural_language: e.target.value })}
              />
            </div>
            <div className='space-y-2'>
              <label className='text-sm font-medium'>Priority (0-100)</label>
              <input
                type='number'
                min={0}
                max={100}
                className='h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm'
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: parseInt(e.target.value, 10) || 0 })}
              />
            </div>
          </div>
          <div className='mt-4 flex justify-end gap-2'>
            <Button variant='outline' onClick={() => setEditPolicy(null)}>Cancel</Button>
            <Button onClick={saveEdit}>Save Changes</Button>
          </div>
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}
