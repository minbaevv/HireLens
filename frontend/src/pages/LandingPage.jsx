import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bot, Mic, BarChart3, Mail, FileDown, Kanban, Star, CheckCircle, Languages, ShieldCheck, Clock, Video, Sparkles, Gauge, Scale, Code2, CalendarClock, Rocket, Building2, Users, Briefcase } from 'lucide-react'
import api from '../api/client'
import { useT } from '../i18n'
import Logo from '../components/Logo'
import LanguageSwitcher from '../components/LanguageSwitcher'
import useReveal from '../hooks/useReveal'

const ICON_MAP = {
  '🤖': Bot, '🎤': Mic, '📊': BarChart3,
  '📧': Mail, '📄': FileDown, '📦': Kanban,
}

export default function LandingPage() {
  const { t, lang } = useT()
  const [data, setData] = useState(null)
  const featuresRef = useReveal()
  const valuePropsRef = useReveal()
  const casesRef = useReveal()
  const pricingRef = useReveal()
  const ctaRef = useReveal()

  useEffect(() => {
    api.get(`/landing?lang=${lang}`).then(r => setData(r.data)).catch(() => {})
  }, [lang])

  // SEO: title, meta, hreflang, JSON-LD (Roadmap D3)
  useEffect(() => {
    if (!data) return
    const title = `${data.product_name} — ${data.tagline}`
    document.title = title
    const setMeta = (attr, key, content) => {
      let el = document.head.querySelector(`meta[${attr}="${key}"]`)
      if (!el) { el = document.createElement('meta'); el.setAttribute(attr, key); document.head.appendChild(el) }
      el.setAttribute('content', content)
    }
    setMeta('name', 'description', data.description)
    setMeta('property', 'og:title', title)
    setMeta('property', 'og:description', data.description)
    setMeta('property', 'og:type', 'website')
    setMeta('name', 'twitter:card', 'summary_large_image')
    document.querySelectorAll('link[data-hreflang]').forEach(el => el.remove())
    const origin = window.location.origin
    ;['ru', 'ky', 'en'].forEach(l => {
      const link = document.createElement('link')
      link.rel = 'alternate'
      link.hreflang = l
      link.href = `${origin}/landing?lang=${l}`
      link.setAttribute('data-hreflang', '1')
      document.head.appendChild(link)
    })
    let ld = document.getElementById('ld-json')
    if (!ld) { ld = document.createElement('script'); ld.type = 'application/ld+json'; ld.id = 'ld-json'; document.head.appendChild(ld) }
    ld.textContent = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'SoftwareApplication',
      name: data.product_name,
      applicationCategory: 'BusinessApplication',
      description: data.description,
      offers: (data.pricing || []).map(p => ({ '@type': 'Offer', name: p.name, price: p.price, priceCurrency: 'KGS' })),
    })
  }, [data])

  return (
    <div className="min-h-screen bg-surface">
      {/* Nav */}
      <nav className="border-b border-line sticky top-0 bg-surface/90 backdrop-blur z-50">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#0b1e3f] rounded-lg flex items-center justify-center">
              <Logo className="w-5 h-5" title="HireLens" gradId="hl-nav" />
            </div>
            <span className="font-bold text-content">HireLens</span>
          </div>
          <div className="flex items-center gap-3">
            <LanguageSwitcher />
            <Link to="/login" className="text-sm text-muted hover:text-content font-medium">{t('login.submit')}</Link>
            <Link to="/register" className="bg-brand-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-brand-700 font-medium">
              {t('landing.startFree')}
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative max-w-6xl mx-auto px-4 pt-20 pb-16 text-center overflow-hidden">
        <div className="absolute inset-0 glow-brand pointer-events-none" aria-hidden="true" />
        <div className="relative">
          <div className="inline-flex items-center gap-2 bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300 text-sm px-4 py-1.5 rounded-full mb-6 font-medium animate-fade-up delay-0">
            <span className="relative flex w-2 h-2">
              <span className="animate-pulse-dot absolute inline-flex h-full w-full rounded-full bg-brand-500" />
            </span>
            <Star className="w-4 h-4" /> {t('landing.badge')}
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold text-content mb-6 leading-tight text-balance animate-fade-up delay-100">
            {data?.tagline || t('landing.heroTitleFallback')}
          </h1>
          <p className="text-xl text-muted max-w-2xl mx-auto mb-10 text-pretty animate-fade-up delay-200">
            {data?.description || t('landing.heroDescFallback')}
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap animate-fade-up delay-300">
            <Link to="/register" className="group bg-brand-600 text-white px-8 py-3.5 rounded-xl hover:bg-brand-700 font-semibold text-lg shadow-lg shadow-brand-200 dark:shadow-none transition-all duration-300 hover:shadow-xl hover:shadow-brand-300/60 hover:-translate-y-0.5">
              {t('landing.tryFree')}
            </Link>
            <a href="#features" className="text-muted px-8 py-3.5 rounded-xl border border-line hover:border-brand-400 hover:text-content font-semibold text-lg transition-colors duration-300">
              {t('landing.learnMore')}
            </a>
          </div>
        </div>
      </section>

      {/* Product preview — стилизованный мокап дашборда (соц. доказательство продуктом) */}
      <section className="max-w-5xl mx-auto px-4 pb-4 animate-fade-up delay-400">
        <div className="rounded-2xl border border-line bg-canvas shadow-xl overflow-hidden animate-float">
          <div className="flex items-center gap-1.5 px-4 h-9 border-b border-line bg-surface-muted">
            <span className="w-3 h-3 rounded-full bg-red-400" />
            <span className="w-3 h-3 rounded-full bg-amber-400" />
            <span className="w-3 h-3 rounded-full bg-green-400" />
            <span className="ml-3 text-xs text-faint">app.gethirelens.tech</span>
          </div>
          <div className="p-5 grid grid-cols-4 gap-3">
            {[
              { c: 'text-brand-600', bg: 'bg-brand-50 dark:bg-brand-500/15', Icon: Kanban },
              { c: 'text-green-600', bg: 'bg-green-50 dark:bg-green-500/15', Icon: CheckCircle },
              { c: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-500/15', Icon: Mic },
              { c: 'text-brand-600', bg: 'bg-brand-50 dark:bg-brand-500/15', Icon: BarChart3 },
            ].map(({ c, bg, Icon }, i) => (
              <div key={i} className="card p-3">
                <div className={`inline-flex p-1.5 rounded-lg ${bg} ${c} mb-2`}><Icon className="w-4 h-4" /></div>
                <div className="h-2.5 w-10 rounded bg-surface-muted mb-1.5" />
                <div className="h-1.5 w-14 rounded bg-line" />
              </div>
            ))}
            <div className="col-span-4 card p-4 flex items-end gap-2 h-28">
              {[40, 65, 45, 80, 55, 70].map((h, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-t bg-brand-500/80 animate-bar-grow transition-colors hover:bg-brand-500"
                  style={{ height: `${h}%`, animationDelay: `${400 + i * 90}ms` }}
                />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Value props — честные преимущества продукта (без накрученных цифр) */}
      <section ref={valuePropsRef} className="reveal border-y border-line bg-canvas py-12">
        <div className="max-w-6xl mx-auto px-4 grid grid-cols-2 md:grid-cols-4 gap-8">
          {[
            { Icon: Languages,  title: t('landing.vp1Title'), sub: t('landing.vp1Sub') },
            { Icon: Video,      title: t('landing.vp2Title'), sub: t('landing.vp2Sub') },
            { Icon: ShieldCheck,title: t('landing.vp3Title'), sub: t('landing.vp3Sub') },
            { Icon: Clock,      title: t('landing.vp4Title'), sub: t('landing.vp4Sub') },
          ].map(({ Icon, title, sub }, i) => (
            <div key={i} className="text-center">
              <div className="inline-flex p-3 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300 mb-3">
                <Icon className="w-6 h-6" />
              </div>
              <div className="text-lg font-bold text-content">{title}</div>
              <div className="text-sm text-muted mt-0.5">{sub}</div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-6xl mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center text-content mb-3 text-balance">{t('landing.howTitle')}</h2>
        <p className="text-center text-muted mb-12 text-pretty">{t('landing.howSubtitle')}</p>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[
            { Icon: Briefcase, title: t('landing.how1Title'), desc: t('landing.how1Desc') },
            { Icon: Mic, title: t('landing.how2Title'), desc: t('landing.how2Desc') },
            { Icon: Gauge, title: t('landing.how3Title'), desc: t('landing.how3Desc') },
            { Icon: CheckCircle, title: t('landing.how4Title'), desc: t('landing.how4Desc') },
          ].map(({ Icon, title, desc }, i) => (
            <div key={i} className="relative p-6 border border-line rounded-2xl bg-surface card-lift">
              <div className="absolute -top-3 -left-3 w-8 h-8 rounded-full bg-brand-600 text-white text-sm font-bold flex items-center justify-center shadow-lg">{i + 1}</div>
              <div className="w-11 h-11 bg-brand-50 dark:bg-brand-500/15 rounded-xl flex items-center justify-center mb-4">
                <Icon className="w-5 h-5 text-brand-600 dark:text-brand-300" />
              </div>
              <h3 className="font-semibold text-content mb-2">{title}</h3>
              <p className="text-muted text-sm">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" ref={featuresRef} className="reveal max-w-6xl mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center text-content mb-12 text-balance">{t('landing.featuresTitle')}</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {(data?.features || []).map((f, i) => {
            const Icon = ICON_MAP[f.icon] || Bot
            return (
              <div key={i} className="group p-6 border border-line rounded-2xl bg-surface card-lift">
                <div className="w-12 h-12 bg-brand-50 dark:bg-brand-500/15 rounded-xl flex items-center justify-center mb-4 transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3">
                  <Icon className="w-6 h-6 text-brand-600 dark:text-brand-300" />
                </div>
                <h3 className="font-semibold text-content mb-2">{f.title}</h3>
                <p className="text-muted text-sm">{f.description}</p>
              </div>
            )
          })}
        </div>
      </section>

      {/* Capabilities — detailed */}
      <section className="bg-canvas border-y border-line py-20">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center text-content mb-3 text-balance">{t('landing.capTitle')}</h2>
          <p className="text-center text-muted mb-12 text-pretty">{t('landing.capSubtitle')}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { Icon: Sparkles, title: t('landing.capAdaptiveTitle'), desc: t('landing.capAdaptiveDesc') },
              { Icon: Gauge, title: t('landing.capScoringTitle'), desc: t('landing.capScoringDesc') },
              { Icon: ShieldCheck, title: t('landing.capAntiCheatTitle'), desc: t('landing.capAntiCheatDesc') },
              { Icon: Scale, title: t('landing.capBiasTitle'), desc: t('landing.capBiasDesc') },
              { Icon: Video, title: t('landing.capVideoTitle'), desc: t('landing.capVideoDesc') },
              { Icon: Code2, title: t('landing.capCodingTitle'), desc: t('landing.capCodingDesc') },
              { Icon: CalendarClock, title: t('landing.capSchedulingTitle'), desc: t('landing.capSchedulingDesc') },
              { Icon: Bot, title: t('landing.capCopilotTitle'), desc: t('landing.capCopilotDesc') },
            ].map(({ Icon, title, desc }, i) => (
              <div key={i} className="p-6 border border-line rounded-2xl bg-surface card-lift">
                <div className="w-11 h-11 bg-brand-50 dark:bg-brand-500/15 rounded-xl flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-brand-600 dark:text-brand-300" />
                </div>
                <h3 className="font-semibold text-content mb-2">{title}</h3>
                <p className="text-muted text-sm">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* For whom — company sizes */}
      <section className="max-w-6xl mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center text-content mb-3 text-balance">{t('landing.segTitle')}</h2>
        <p className="text-center text-muted mb-12 text-pretty">{t('landing.segSubtitle')}</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { Icon: Rocket, title: t('landing.segSmallTitle'), desc: t('landing.segSmallDesc') },
            { Icon: Building2, title: t('landing.segMidTitle'), desc: t('landing.segMidDesc') },
            { Icon: Users, title: t('landing.segLargeTitle'), desc: t('landing.segLargeDesc') },
          ].map(({ Icon, title, desc }, i) => (
            <div key={i} className="p-8 border border-line rounded-2xl bg-surface card-lift text-center">
              <div className="inline-flex p-3 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300 mb-4">
                <Icon className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-content mb-2">{title}</h3>
              <p className="text-muted text-sm">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section ref={pricingRef} className="reveal bg-canvas py-20">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center text-content mb-12 text-balance">{t('landing.pricingTitle')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {(data?.pricing || []).map((plan, i) => (
              <div key={i} className={`p-8 rounded-2xl border-2 transition-all duration-base hover:-translate-y-1.5 hover:shadow-glow-accent ${
                plan.highlighted
                  ? 'border-brand-600 bg-brand-600 text-white shadow-xl shadow-brand-200 dark:shadow-none md:scale-105 hover:shadow-2xl hover:shadow-brand-300/50'
                  : 'border-line bg-surface hover:border-brand-400 hover:shadow-lg'
              }`}>
                <div className={`text-sm font-semibold mb-2 ${
                  plan.highlighted ? 'text-brand-200' : 'text-muted'
                }`}>{plan.name}</div>
                <div className="flex items-end gap-1 mb-6">
                  <span className="text-4xl font-extrabold">{plan.price} {plan.currency || 'сом'}</span>
                  <span className={`text-sm mb-1 ${plan.highlighted ? 'text-brand-200' : 'text-faint'}`}>/{plan.period}</span>
                </div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feat, j) => (
                    <li key={j} className="flex items-center gap-2 text-sm">
                      <CheckCircle className={`w-4 h-4 flex-shrink-0 ${
                        plan.highlighted ? 'text-brand-200' : 'text-brand-600 dark:text-brand-300'
                      }`} />
                      {feat}
                    </li>
                  ))}
                </ul>
                <Link to="/register" className={`block text-center py-2.5 rounded-xl font-semibold text-sm ${
                  plan.highlighted
                    ? 'bg-white text-brand-600 hover:bg-brand-50'
                    : 'bg-brand-600 text-white hover:bg-brand-700'
                }`}>
                  {t('landing.planStart')}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use cases (Roadmap D3) */}
      {(data?.cases?.length > 0) && (
        <section ref={casesRef} className="reveal max-w-6xl mx-auto px-4 py-20">
          <h2 className="text-3xl font-bold text-center text-content mb-3 text-balance">{t('landing.casesTitle')}</h2>
          <p className="text-center text-muted mb-12 text-pretty">{t('landing.casesSubtitle')}</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {data.cases.map((c, i) => (
              <div key={i} className="p-6 border border-line rounded-2xl bg-surface card-lift">
                <div className="text-xs font-semibold text-brand-600 dark:text-brand-300 uppercase tracking-wide mb-2">{c.industry}</div>
                <p className="text-content font-semibold mb-2">{c.challenge}</p>
                <p className="text-muted text-sm mb-4">{c.solution}</p>
                <div className="text-sm font-semibold text-brand-700 dark:text-brand-300">→ {c.outcome}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* CTA */}
      <section ref={ctaRef} className="reveal relative max-w-6xl mx-auto px-4 py-20 text-center overflow-hidden">
        <div className="absolute inset-0 glow-brand pointer-events-none" aria-hidden="true" />
        <div className="relative">
          <h2 className="text-3xl font-bold text-content mb-4 text-balance">{t('landing.ctaTitle')}</h2>
          <p className="text-muted mb-8 text-pretty">{t('landing.ctaSubtitle')}</p>
          <Link to="/register" className="inline-block bg-brand-600 text-white px-10 py-4 rounded-xl hover:bg-brand-700 font-semibold text-lg shadow-lg shadow-brand-200 dark:shadow-none transition-all duration-300 hover:shadow-xl hover:shadow-brand-300/60 hover:-translate-y-0.5">
            {t('landing.startFree')}
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-line py-8">
        <div className="max-w-6xl mx-auto px-4 flex items-center justify-between text-sm text-faint">
          <span>{t('landing.footerCopyright')}</span>
          <span>{data?.contact_email}</span>
        </div>
      </footer>
    </div>
  )
}
