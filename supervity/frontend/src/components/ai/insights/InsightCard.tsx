'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import { Icons } from '@/components/ui/icons'
import { Button } from '@/components/ui/button'

export type InsightSeverity = 'critical' | 'high' | 'warning' | 'medium' | 'low' | 'info'
export type InsightType = 'pattern' | 'anomaly' | 'recommendation' | 'trend' | 'alert'

export interface Insight {
  id: string
  type: InsightType
  severity: InsightSeverity
  title: string
  description: string
  data?: Record<string, unknown>
  /** WHO this insight is for */
  owner_name?: string
  owner_role?: string
  owner_id?: string
  /** WHAT they should do now */
  suggested_action?: string
  /** WHAT happens if they don't */
  consequence?: string
  action_type?: string
  confidence?: number
  created_at: string
  is_dismissed?: boolean
  is_actioned?: boolean
}

interface InsightCardProps {
  insight: Insight
  onAction?: (insight: Insight) => void
  onDismiss?: (id: string) => void
}

/**
 * Get severity configuration for consistent styling across the app.
 * Supports both old severity names and new ones.
 */
export function getSeverityConfig(severity: InsightSeverity) {
  const configs = {
    critical: {
      icon: Icons.alertCircle,
      bg: 'bg-red-50',
      border: 'border-red-200',
      accent: 'border-l-red-500',
      iconBg: 'bg-red-100',
      iconColor: 'text-red-600',
      badge: 'bg-red-100 text-red-700',
      textColor: 'text-red-700',
    },
    high: {
      icon: Icons.alertCircle,
      bg: 'bg-red-50/70',
      border: 'border-red-200',
      accent: 'border-l-red-400',
      iconBg: 'bg-red-100',
      iconColor: 'text-red-500',
      badge: 'bg-red-100 text-red-600',
      textColor: 'text-red-600',
    },
    warning: {
      icon: Icons.alertTriangle,
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      accent: 'border-l-amber-500',
      iconBg: 'bg-amber-100',
      iconColor: 'text-amber-600',
      badge: 'bg-amber-100 text-amber-700',
      textColor: 'text-amber-700',
    },
    medium: {
      icon: Icons.alertTriangle,
      bg: 'bg-amber-50/70',
      border: 'border-amber-200',
      accent: 'border-l-amber-400',
      iconBg: 'bg-amber-100',
      iconColor: 'text-amber-500',
      badge: 'bg-amber-100 text-amber-600',
      textColor: 'text-amber-600',
    },
    low: {
      icon: Icons.info,
      bg: 'bg-sky-50/70',
      border: 'border-sky-200',
      accent: 'border-l-sky-400',
      iconBg: 'bg-sky-100',
      iconColor: 'text-sky-500',
      badge: 'bg-sky-100 text-sky-600',
      textColor: 'text-sky-600',
    },
    info: {
      icon: Icons.info,
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      accent: 'border-l-blue-500',
      iconBg: 'bg-blue-100',
      iconColor: 'text-blue-600',
      badge: 'bg-blue-100 text-blue-700',
      textColor: 'text-blue-700',
    },
  }
  return configs[severity] || configs.info
}

const typeConfig: Record<InsightType, { label: string; icon: typeof Icons.activity }> = {
  pattern: { label: 'Pattern', icon: Icons.activity },
  anomaly: { label: 'Anomaly', icon: Icons.alertTriangle },
  recommendation: { label: 'Recommendation', icon: Icons.lightbulb },
  trend: { label: 'Trend', icon: Icons.trendingUp },
  alert: { label: 'Alert', icon: Icons.bell },
}

export function InsightCard({ insight, onAction, onDismiss }: InsightCardProps) {
  const [showTrace, setShowTrace] = useState(false)
  const severity = getSeverityConfig(insight.severity)
  const type = typeConfig[insight.type] || typeConfig.recommendation
  const SeverityIcon = severity.icon
  const trace = insight.data?.ai_trace as { step?: number; action: string; detail: string }[] | undefined
  const auditKeys = ['ai_trace', 'model_used', 'llm_notice']

  return (
    <div className={cn(
      'rounded-xl border p-4',
      'transition-all duration-200 hover:shadow-soft',
      severity.bg,
      severity.border
    )}>
      <div className="flex gap-4">
        {/* Icon */}
        <div className={cn(
          'flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg',
          severity.iconBg
        )}>
          <SeverityIcon className={cn('h-5 w-5', severity.iconColor)} strokeWidth={1.5} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <h4 className="font-semibold text-foreground">{insight.title}</h4>
                <span className={cn(
                  'rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase',
                  severity.badge
                )}>
                  {insight.severity}
                </span>
                {insight.confidence && (
                  <span className="text-xs text-muted-foreground">
                    {Math.round(insight.confidence * 100)}% confident
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <type.icon className="h-3 w-3 text-muted-foreground" strokeWidth={1.5} />
                <span className="text-xs text-muted-foreground">{type.label}</span>
                <span className="text-xs text-muted-foreground">•</span>
                <span className="text-xs text-muted-foreground">
                  {new Date(insight.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            
            {onDismiss && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => onDismiss(insight.id)}
                className="text-muted-foreground hover:text-foreground"
              >
                <Icons.close className="h-4 w-4" />
              </Button>
            )}
          </div>

          <p className="mt-2 text-sm text-muted-foreground">
            {insight.description}
          </p>

          {/* Data preview */}
          {insight.data && Object.keys(insight.data).filter(k => !auditKeys.includes(k)).length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {Object.entries(insight.data)
                .filter(([key]) => !auditKeys.includes(key))
                .slice(0, 3)
                .map(([key, value]) => (
                  <span
                    key={key}
                    className={cn(
                      'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1',
                      'bg-white/50 text-xs font-medium text-foreground'
                    )}
                  >
                    <span className="text-muted-foreground">{key.replace(/_/g, ' ')}:</span>
                    <span className="font-semibold">{String(value)}</span>
                  </span>
                ))}
            </div>
          )}

          {/* Deep auditability: AI reasoning trace */}
          {trace && trace.length > 0 && (
            <div className="mt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowTrace(!showTrace)}
              >
                <Icons.brain className="mr-1.5 h-3.5 w-3.5" strokeWidth={1.5} />
                {showTrace ? 'Hide AI Trace' : 'View AI Trace'}
              </Button>
              {showTrace && (
                <div className="mt-3 p-3 bg-slate-900 rounded-md text-xs text-slate-50 font-mono overflow-x-auto">
                  <ol className="list-decimal pl-4 space-y-2">
                    {trace.map((step, i) => (
                      <li key={i}>
                        <strong>{step.action}</strong>: {step.detail}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          )}

          {/* WHO / DO NOW / IF IGNORED */}
          {(insight.owner_name || insight.suggested_action || insight.consequence) && (
            <div className="mt-4 space-y-2 rounded-lg border border-white/60 bg-white/50 p-3">
              {/* WHO is this for */}
              {insight.owner_name && (
                <div className="flex items-start gap-2">
                  <Icons.user className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" strokeWidth={1.5} />
                  <p className="text-sm">
                    <span className="font-semibold uppercase tracking-wide text-[10px] text-muted-foreground mr-1.5">
                      For
                    </span>
                    <span className="font-semibold text-foreground">{insight.owner_name}</span>
                    {insight.owner_role && (
                      <span className="text-muted-foreground"> — {insight.owner_role}</span>
                    )}
                  </p>
                </div>
              )}

              {/* WHAT to do now */}
              {insight.suggested_action && (
                <div className="flex items-start gap-2">
                  <Icons.zap className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-emerald-600" strokeWidth={1.5} />
                  <p className="text-sm text-foreground">
                    <span className="font-semibold uppercase tracking-wide text-[10px] text-emerald-700 mr-1.5">
                      Do now
                    </span>
                    {insight.suggested_action}
                  </p>
                </div>
              )}

              {/* WHAT happens if they don't */}
              {insight.consequence && (
                <div className="flex items-start gap-2">
                  <Icons.alertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-red-500" strokeWidth={1.5} />
                  <p className="text-sm text-foreground">
                    <span className="font-semibold uppercase tracking-wide text-[10px] text-red-600 mr-1.5">
                      If ignored
                    </span>
                    {insight.consequence}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Action button */}
          {insight.suggested_action && (
            <div className="mt-3 flex items-center gap-3">
              <Button
                variant="default"
                size="sm"
                onClick={() => onAction?.(insight)}
              >
                <Icons.zap className="mr-1.5 h-3.5 w-3.5" strokeWidth={1.5} />
                Take this action
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

