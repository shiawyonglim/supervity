'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Icons } from '@/components/ui/icons'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api-client'
import { Badge } from '@/components/ui/badge'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

type TabType = 'buying-groups' | 'routing' | 'consent' | 'integrations'

const tabs = [
  { id: 'buying-groups' as TabType, label: 'Buying Groups', icon: Icons.users },
  { id: 'routing' as TabType, label: 'Routing & Territories', icon: Icons.share },
  { id: 'consent' as TabType, label: 'Consent Registry', icon: Icons.checkCircle },
  { id: 'integrations' as TabType, label: 'Integrations', icon: Icons.zap },
]

export default function DataManagerPage() {
  const [activeTab, setActiveTab] = useState<TabType>('buying-groups')
  const [data, setData] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(false)

  const fetchData = useCallback(async (tab: TabType) => {
    setIsLoading(true)
    try {
      const endpoint = `/api/data-manager/${tab}`
      const response = await apiClient.get<any>(endpoint)
      setData(response)
    } catch (err) {
      console.error(`Failed to load ${tab}:`, err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData(activeTab)
  }, [activeTab, fetchData])

  const renderContent = () => {
    if (isLoading) {
      return <div className="flex justify-center p-12"><Icons.loader className="h-8 w-8 animate-spin text-muted-foreground" /></div>
    }

    if (!data) return null

    switch (activeTab) {
      case 'buying-groups':
        return (
          <div className="space-y-4">
            {data.buying_groups?.map((bg: any) => (
              <Card key={bg.group_id} className="bg-white">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">{bg.account_name}</CardTitle>
                  <CardDescription>{bg.account_industry}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 mt-2">
                    {bg.contacts?.map((c: any) => (
                      <div key={c.contact_id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg border">
                        <div>
                          <p className="font-medium text-sm text-brand-navy">{c.name} {c.is_primary && <Badge variant="default" className="ml-2 text-[10px]">Primary</Badge>}</p>
                          <p className="text-xs text-muted-foreground">{c.title} • {c.email}</p>
                        </div>
                        <Badge variant="outline">{c.role}</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )

      case 'routing':
        return (
          <div className="grid md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Routing Rules</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.routing_rules?.map((rule: any) => (
                    <div key={rule.rule_id} className="p-3 border rounded-lg">
                      <p className="font-semibold text-sm">{rule.rule_name}</p>
                      <p className="text-xs text-muted-foreground mt-1 font-mono bg-gray-50 p-1 rounded">
                        {rule.condition} ➔ {rule.action}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Territories</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.territories?.map((t: any) => (
                    <div key={t.territory_id} className="flex justify-between p-3 border rounded-lg">
                      <span className="font-medium text-sm">{t.territory_name}</span>
                      <span className="text-xs text-muted-foreground">{t.region}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )

      case 'consent':
        return (
          <Card>
            <CardHeader>
              <CardTitle>Consent Registry</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-muted-foreground bg-gray-50 uppercase">
                    <tr>
                      <th className="px-4 py-3 rounded-tl-lg">Contact</th>
                      <th className="px-4 py-3">Region</th>
                      <th className="px-4 py-3">Basis</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 rounded-tr-lg">Channel</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.consent_records?.map((record: any) => (
                      <tr key={record.consent_id} className="border-b last:border-0">
                        <td className="px-4 py-3 font-medium text-brand-navy">{record.contact_name}</td>
                        <td className="px-4 py-3">{record.region}</td>
                        <td className="px-4 py-3">{record.basis}</td>
                        <td className="px-4 py-3">
                          <Badge variant={record.status === 'granted' ? 'default' : 'secondary'}>{record.status}</Badge>
                        </td>
                        <td className="px-4 py-3">{record.channel}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )

      case 'integrations':
        return (
          <div className="grid md:grid-cols-2 gap-4">
            {data.integrations?.map((integ: any, idx: number) => (
              <Card key={idx}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <CardTitle className="text-base">{integ.name}</CardTitle>
                    <Badge variant={integ.status === 'healthy' ? 'default' : 'destructive'} className={integ.status === 'healthy' ? 'bg-emerald-500 hover:bg-emerald-600' : ''}>
                      {integ.status}
                    </Badge>
                  </div>
                  <CardDescription>{integ.type}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{integ.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )

      default:
        return null
    }
  }

  return (
    <motion.div className="space-y-8" variants={containerVariants} initial="hidden" animate="visible">
      <motion.div variants={itemVariants}>
        <h1 className="text-display-3 font-bold tracking-tight text-brand-navy">Data Manager</h1>
        <p className="mt-2 text-lg text-muted-foreground">Manage your centralized master data, routing, and integrations.</p>
      </motion.div>

      <motion.div variants={itemVariants} className="flex space-x-1 border-b">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center space-x-2 px-4 py-2 text-sm font-medium transition-colors border-b-2',
                isActive
                  ? 'border-brand-cornflower text-brand-navy'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </motion.div>

      <motion.div variants={itemVariants}>
        {renderContent()}
      </motion.div>
    </motion.div>
  )
}
