'use client'

import { cn } from '@/lib/utils'
import { useRole, ALL_ROLES, ROLE_META, type AppRole } from '@/context/RoleContext'
import { Icons } from '@/components/ui/icons'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'

export function RoleSwitcher() {
  const { activeRole, setRole, roleLabel, roleMeta } = useRole()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className={cn(
            'group flex h-9 items-center gap-2 rounded-full border px-3 text-sm font-medium transition-all',
            'border-black/[0.06] bg-white/80 hover:bg-white hover:shadow-sm',
            'focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50'
          )}
          aria-label='Switch role'
        >
          <span
            className={cn(
              'rounded-md border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide',
              roleMeta.color
            )}
          >
            {roleMeta.shortLabel}
          </span>
          <span className='hidden text-muted-foreground group-hover:text-foreground sm:inline'>
            {roleLabel}
          </span>
          <Icons.chevronDown
            className={cn(
              'h-4 w-4 text-muted-foreground transition-transform duration-200',
              'group-data-[state=open]:rotate-180'
            )}
          />
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align='end' className='w-56'>
        <DropdownMenuLabel className='text-xs font-semibold text-muted-foreground'>
          Switch role
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {ALL_ROLES.map((role: AppRole) => {
          const meta = ROLE_META[role]
          const isActive = role === activeRole
          return (
            <DropdownMenuItem
              key={role}
              onClick={() => setRole(role)}
              className={cn(
                'flex cursor-pointer items-center justify-between gap-2',
                isActive && 'bg-muted'
              )}
            >
              <div className='flex items-center gap-2'>
                <span
                  className={cn(
                    'rounded border px-1.5 py-0.5 text-[10px] font-bold uppercase',
                    meta.color
                  )}
                >
                  {meta.shortLabel}
                </span>
                <span className='text-sm'>{meta.label}</span>
              </div>
              {isActive && <Icons.check className='h-4 w-4 text-brand-cornflower' />}
            </DropdownMenuItem>
          )
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
