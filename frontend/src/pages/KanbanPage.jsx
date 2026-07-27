import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  DndContext,
  DragOverlay,
  useDroppable,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import api from '../api/client'
import ScoreBadge from '../components/ScoreBadge'
import RecommendationBadge from '../components/RecommendationBadge'
import Spinner from '../components/Spinner'
import { useT } from '../i18n'
import { useAuth } from '../hooks/useAuth'
import { GripVertical, Inbox, Mic, CheckCircle, UserCheck, UserX, CalendarClock } from 'lucide-react'

// Иконки и цвета колонок по статусу (эмодзи из бэкенда не используем —
// они по-разному рендерятся на разных ОС и выглядят неаккуратно в B2B).
const COLUMN_META = {
  applied:      { icon: Inbox,       color: 'text-blue-500' },
  interviewing: { icon: Mic,         color: 'text-amber-500' },
  completed:    { icon: CheckCircle, color: 'text-slate-400' },
  invited:      { icon: CalendarClock, color: 'text-purple-500' },
  hired:        { icon: UserCheck,   color: 'text-green-500' },
  rejected:     { icon: UserX,       color: 'text-red-500' },
}
const STATUS_LABEL_KEYS = {
  applied: 'status.applied',
  interviewing: 'status.interviewing',
  completed: 'status.completed',
  invited: 'status.invited',
  hired: 'status.hired',
  rejected: 'status.rejected',
}

function CandidateCard({ candidate, isDragging = false }) {
  const { t } = useT()

  return (
    <div className={`bg-surface border border-line rounded-xl p-4 shadow-e1 hover:shadow-e2 transition-shadow duration-base ${isDragging ? 'opacity-50' : ''}`}>
      <div className="flex items-start gap-2">
        <GripVertical className="w-4 h-4 text-faint flex-shrink-0 mt-0.5 cursor-grab" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-content truncate">{candidate.name}</p>
          <p className="text-xs text-faint truncate mb-3">{candidate.email}</p>
          <div className="flex items-center gap-2">
            <ScoreBadge score={candidate.score} />
            <RecommendationBadge value={candidate.recommendation} />
          </div>
        </div>
      </div>
    </div>
  )
}

function SortableCard({ candidate }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: candidate.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Link to={`/candidates/${candidate.id}`} onClick={(e) => isDragging && e.preventDefault()}>
        <CandidateCard candidate={candidate} isDragging={isDragging} />
      </Link>
    </div>
  )
}

// Колонка-дропзона: подсвечивается при наведении перетаскиваемой карточки.
function DroppableColumn({ status, children }) {
  const { setNodeRef, isOver } = useDroppable({ id: status })
  return (
    <div
      ref={setNodeRef}
      id={status}
      className={`flex-1 space-y-3 min-h-[200px] rounded-xl p-3 border-2 border-dashed transition-colors duration-base ${
        isOver
          ? 'border-brand-400 bg-brand-50/70 dark:border-brand-500/50 dark:bg-brand-500/10'
          : 'border-line bg-surface-muted'
      }`}
    >
      {children}
    </div>
  )
}

export default function KanbanPage() {
  const { t } = useT()
  const { canWrite } = useAuth()
  const [board, setBoard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeId, setActiveId] = useState(null)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px движения до начала драга
      },
    })
  )

  useEffect(() => {
    loadBoard()
  }, [])

  async function loadBoard() {
    try {
      const { data } = await api.get('/candidates/kanban')
      setBoard(data)
    } finally {
      setLoading(false)
    }
  }

  function handleDragStart(event) {
    setActiveId(event.active.id)
  }

  async function handleDragEnd(event) {
    const { active, over } = event
    setActiveId(null)

    if (!canWrite) return
    if (!over) return

    const candidateId = active.id
    const targetStatus = over.id

    // Если бросили на ту же колонку — ничего не делаем
    const currentColumn = board.columns.find(col =>
      col.candidates.some(c => c.id === candidateId)
    )
    if (currentColumn?.status === targetStatus) return

    // Оптимистичное обновление UI
    const newColumns = board.columns.map(col => ({
      ...col,
      candidates: col.status === targetStatus
        ? [...col.candidates, currentColumn.candidates.find(c => c.id === candidateId)]
        : col.candidates.filter(c => c.id !== candidateId),
      count: col.status === targetStatus
        ? col.count + 1
        : col.status === currentColumn.status
        ? col.count - 1
        : col.count,
    }))

    setBoard({ ...board, columns: newColumns })

    // Отправляем на backend
    try {
      await api.patch(`/candidates/${candidateId}/stage?new_stage=${targetStatus}`)
    } catch (err) {
      console.error('Failed to update stage:', err)
      // Rollback при ошибке
      loadBoard()
    }
  }

  if (loading) return <div className="flex items-center justify-center h-full"><Spinner size="lg" /></div>
  if (!board) return null

  const activeCandidate = activeId
    ? board.columns.flatMap(col => col.candidates).find(c => c.id === activeId)
    : null

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="p-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-content">{t('kanban.title')}</h1>
          <p className="text-muted mt-1">{t('candidates.countSuffix', { count: board.total })}</p>
        </div>

        <div className="flex gap-4 overflow-x-auto pb-4 items-stretch">
          {board.columns.map(col => {
            const meta = COLUMN_META[col.status] ?? { icon: Inbox, color: 'text-faint' }
            const Icon = meta.icon
            const label = STATUS_LABEL_KEYS[col.status] ? t(STATUS_LABEL_KEYS[col.status]) : col.label
            return (
            <SortableContext
              key={col.status}
              id={col.status}
              items={col.candidates.map(c => c.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="flex-shrink-0 w-72 flex flex-col">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-content flex items-center gap-2">
                    <Icon className={`w-4 h-4 ${meta.color}`} /> {label}
                  </h2>
                  <span className="text-xs bg-surface-muted text-muted px-2 py-0.5 rounded-full font-medium">
                    {col.count}
                  </span>
                </div>
                <DroppableColumn status={col.status}>
                  {col.candidates.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full py-8 text-center">
                      <Icon className={`w-8 h-8 mb-2 opacity-25 ${meta.color}`} />
                      <p className="text-xs text-faint">{t('kanban.emptyHint')}</p>
                    </div>
                  ) : (
                    col.candidates.map(c => (
                      <SortableCard key={c.id} candidate={c} />
                    ))
                  )}
                </DroppableColumn>
              </div>
            </SortableContext>
            )
          })}
        </div>
      </div>

      <DragOverlay>
        {activeCandidate ? <div className="scale-[1.03] cursor-grabbing"><CandidateCard candidate={activeCandidate} /></div> : null}
      </DragOverlay>
    </DndContext>
  )
}
