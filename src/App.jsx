import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload, FileText, CheckCircle, Zap, Shield, Search,
  ArrowRight, Bell, BarChart2, RefreshCw, Download,
  AlertCircle, ChevronDown, ChevronUp, X
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

// ── 유틸리티 ──────────────────────────────────────────────────────────────
const scoreColor = (score) => {
  if (score >= 0.8) return '#22c55e';
  if (score >= 0.6) return '#f59e0b';
  return '#ef4444';
};

const formatDate = (d) => d ? d.replace(/(\d{4})(\d{2})(\d{2})/, '$1.$2.$3') : '미정';

// ── 공고 카드 ────────────────────────────────────────────────────────────
const GrantCard = ({ match, onGenerate }) => {
  const [open, setOpen] = useState(false);
  const dDay = (() => {
    if (!match.end_date || match.end_date.length < 8) return null;
    const end = new Date(match.end_date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3'));
    const diff = Math.ceil((end - new Date()) / 86400000);
    return diff;
  })();

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-2xl overflow-hidden"
    >
      <div
        className="p-5 cursor-pointer hover:bg-white/[0.03] transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <p className="text-xs text-slate-500 mb-1">{match.org || match.source}</p>
            <h3 className="font-semibold text-sm leading-snug truncate">{match.title}</h3>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {dDay !== null && (
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                dDay <= 7 ? 'bg-red-500/20 text-red-400' :
                dDay <= 30 ? 'bg-amber-500/20 text-amber-400' :
                'bg-slate-700 text-slate-400'
              }`}>
                {dDay <= 0 ? '마감' : `D-${dDay}`}
              </span>
            )}
            <div className="text-right">
              <div className="text-xs text-slate-500">매칭</div>
              <div className="font-bold text-sm" style={{ color: scoreColor(match.score) }}>
                {Math.round((match.score || 0) * 100)}%
              </div>
            </div>
            {open ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-white/5 p-5 space-y-3"
          >
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-slate-500">마감일</span><br /><span className="font-medium">{formatDate(match.end_date)}</span></div>
              <div><span className="text-slate-500">지원금액</span><br /><span className="font-medium">{match.amount || '공고 확인'}</span></div>
            </div>
            {match.reason && (
              <p className="text-xs text-slate-400 bg-white/5 rounded-lg p-3">{match.reason}</p>
            )}
            <div className="flex gap-2">
              {match.url && (
                <a href={match.url} target="_blank" rel="noreferrer"
                  className="flex-1 text-center text-xs py-2 glass rounded-lg hover:bg-white/10 transition-colors">
                  공고 원문 보기
                </a>
              )}
              <button
                onClick={() => onGenerate(match)}
                className="flex-1 flex items-center justify-center gap-1.5 text-xs py-2 bg-primary/20 text-primary rounded-lg hover:bg-primary/30 transition-colors font-semibold"
              >
                <FileText className="w-3.5 h-3.5" /> 계획서 자동 생성
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// ── 생성 결과 패널 ───────────────────────────────────────────────────────
const ProposalResult = ({ result, onClose }) => (
  <motion.div
    initial={{ opacity: 0, x: 40 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: 40 }}
    className="fixed right-0 top-0 h-full w-full max-w-2xl bg-[#0d0d1a] border-l border-white/5 z-50 overflow-y-auto"
  >
    <div className="sticky top-0 bg-[#0d0d1a] border-b border-white/5 p-5 flex items-center justify-between z-10">
      <div>
        <h2 className="font-bold text-lg">계획서 생성 완료</h2>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-sm font-bold" style={{ color: scoreColor(result.score_prediction) }}>
            합격 가능성 {Math.round((result.score_prediction || 0) * 100)}%
          </span>
          <span className="text-slate-500 text-sm">{result.grade} · {result.estimated_score}점</span>
        </div>
      </div>
      <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
        <X className="w-5 h-5" />
      </button>
    </div>

    <div className="p-5 space-y-4">
      {/* Self-Refinement 로그 */}
      {result.refinement_log?.length > 0 && (
        <div className="glass rounded-xl p-4">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Self-Refinement 과정</h3>
          <div className="flex items-end gap-3">
            {result.refinement_log.map((r, i) => (
              <div key={i} className="text-center flex-1">
                <div className="text-xs text-slate-500 mb-1">R{r.round}</div>
                <div className="h-16 flex items-end justify-center">
                  <div
                    className="w-full rounded-t transition-all"
                    style={{
                      height: `${(r.score / 100) * 64}px`,
                      backgroundColor: scoreColor(r.pass_probability)
                    }}
                  />
                </div>
                <div className="text-xs font-bold mt-1" style={{ color: scoreColor(r.pass_probability) }}>
                  {r.score}점
                </div>
              </div>
            ))}
            <div className="text-center flex-1">
              <div className="text-xs text-slate-500 mb-1">최종</div>
              <div className="h-16 flex items-end justify-center">
                <div
                  className="w-full rounded-t"
                  style={{
                    height: `${(result.estimated_score / 100) * 64}px`,
                    backgroundColor: scoreColor(result.score_prediction)
                  }}
                />
              </div>
              <div className="text-xs font-bold mt-1" style={{ color: scoreColor(result.score_prediction) }}>
                {result.estimated_score}점
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 강점 / 약점 */}
      <div className="grid grid-cols-2 gap-3">
        {result.strengths?.length > 0 && (
          <div className="glass rounded-xl p-4">
            <h3 className="text-xs font-bold text-green-400 mb-2">강점</h3>
            <ul className="space-y-1">
              {result.strengths.map((s, i) => (
                <li key={i} className="text-xs text-slate-300 flex gap-1.5">
                  <CheckCircle className="w-3.5 h-3.5 text-green-400 shrink-0 mt-0.5" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}
        {result.weaknesses?.length > 0 && (
          <div className="glass rounded-xl p-4">
            <h3 className="text-xs font-bold text-amber-400 mb-2">보완 권고</h3>
            <ul className="space-y-1">
              {result.weaknesses.map((w, i) => (
                <li key={i} className="text-xs text-slate-300 flex gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                  {w.issue || w}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* 계획서 본문 */}
      <div className="glass rounded-xl p-5">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">계획서 본문</h3>
        <pre className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed font-mono max-h-[60vh] overflow-y-auto">
          {result.proposal_text}
        </pre>
      </div>

      <button
        onClick={() => {
          const blob = new Blob([result.proposal_text], { type: 'text/plain;charset=utf-8' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'GrantAI_사업계획서.txt';
          a.click();
        }}
        className="w-full flex items-center justify-center gap-2 py-3 bg-primary/20 text-primary rounded-xl hover:bg-primary/30 transition-colors font-semibold"
      >
        <Download className="w-4 h-4" /> TXT 다운로드 (복사 후 HWP 편집)
      </button>
    </div>
  </motion.div>
);

// ── 메인 앱 ──────────────────────────────────────────────────────────────
const App = () => {
  const [phase, setPhase] = useState('upload');   // upload | info | matches | generating | result
  const [file, setFile] = useState(null);
  const [companyInfo, setCompanyInfo] = useState(null);
  const [matches, setMatches] = useState([]);
  const [customerId, setCustomerId] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState(0);
  const [proposalResult, setProposalResult] = useState(null);
  const [error, setError] = useState('');

  const genSteps = [
    '공고 평가기준 분석 중...',
    'PSST 초안 작성 중 (Claude Opus)...',
    'Self-Refinement Round 1 — 심사관 피드백...',
    'Self-Refinement Round 2 — 약점 보강...',
    'Self-Refinement Round 3 — 최종 완성...',
    '합격 가능성 분석 완료!',
  ];

  // 파일 업로드 + Claude Vision 분석
  const handleFileUpload = useCallback(async (uploadedFile) => {
    setFile(uploadedFile);
    setPhase('analyzing');
    setError('');
    try {
      const fd = new FormData();
      fd.append('file', uploadedFile);
      const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setCompanyInfo(data);
      setPhase('info');
    } catch (e) {
      setError(`파일 분석 오류: ${e.message}`);
      setPhase('upload');
    }
  }, []);

  // 공고 매칭 요청
  const handleMatchRequest = useCallback(async (info) => {
    setPhase('matching');
    setError('');
    try {
      const res = await fetch(`${API_BASE}/match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: info.company_name || '내 회사',
          industry: info.industry || '',
          keywords: info.keywords || [],
          description: info.market_description || '',
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setCustomerId(data.customer_id);
      setMatches(data.matches || []);
      setPhase('matches');
    } catch (e) {
      setError(`공고 매칭 오류: ${e.message}`);
      setPhase('info');
    }
  }, []);

  // 계획서 생성
  const handleGenerate = useCallback(async (match) => {
    setGenerating(true);
    setGenerationStep(0);
    setError('');

    // 스텝 애니메이션
    const interval = setInterval(() => {
      setGenerationStep(s => Math.min(s + 1, genSteps.length - 1));
    }, 3500);

    try {
      const res = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_id: customerId || 0,
          announcement_id: match.id || '',
          company_info: companyInfo || {},
          run_refinement: true,
        }),
      });
      clearInterval(interval);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setGenerationStep(genSteps.length - 1);
      setProposalResult(data);
    } catch (e) {
      clearInterval(interval);
      setError(`계획서 생성 오류: ${e.message}`);
    } finally {
      setGenerating(false);
    }
  }, [customerId, companyInfo]);

  return (
    <div className="min-h-screen">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-40 glass">
        <div className="container h-16 flex items-center justify-between">
          <div className="text-xl font-black gradient-text tracking-tighter">GrantAI.</div>
          <div className="hidden md:flex gap-6 text-sm font-medium text-slate-400">
            <a href="#how-it-works" className="hover:text-white transition-colors">이용방법</a>
            <a href="#pricing" className="hover:text-white transition-colors">가격</a>
          </div>
          <button className="px-4 py-1.5 glass rounded-full text-sm font-semibold hover:bg-white/10 transition-colors">
            문의하기
          </button>
        </div>
      </nav>

      {/* Main */}
      <main className="pt-24 pb-20 container">
        <div className="max-w-5xl mx-auto">

          {/* Hero */}
          <div className="text-center mb-12">
            <motion.div
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-4 py-1.5 glass rounded-full text-xs font-bold text-primary mb-6 tracking-widest uppercase"
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
              </span>
              실시간 공고 매칭 · AI 계획서 자동 생성
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
              className="text-4xl md:text-5xl font-black mb-4"
            >
              회사 파일 하나로<br />
              <span className="gradient-text">승인되는 계획서</span>를 받아보세요.
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
              className="text-slate-400 text-lg"
            >
              공고 자동 탐지 → Deep Search 초안 작성 → Self-Refinement 3라운드 → HWP 제출
            </motion.p>
          </div>

          {/* Steps Progress */}
          <div className="flex items-center justify-center gap-2 mb-10 text-xs">
            {['파일 업로드', '정보 확인', '공고 매칭', '계획서 생성'].map((label, i) => {
              const phaseIdx = ['upload', 'analyzing', 'info', 'matching', 'matches'].indexOf(phase);
              const active = phaseIdx >= i;
              return (
                <React.Fragment key={i}>
                  <div className={`px-3 py-1.5 rounded-full font-semibold transition-colors ${active ? 'bg-primary/20 text-primary' : 'glass text-slate-500'}`}>
                    {i + 1}. {label}
                  </div>
                  {i < 3 && <div className={`h-px w-6 ${active ? 'bg-primary/40' : 'bg-white/10'}`} />}
                </React.Fragment>
              );
            })}
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" /> {error}
            </div>
          )}

          {/* Phase: Upload */}
          <AnimatePresence mode="wait">
            {(phase === 'upload' || phase === 'analyzing') && (
              <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="max-w-xl mx-auto"
              >
                <label className="group relative flex flex-col items-center justify-center w-full h-64 glass rounded-3xl border-dashed border-2 border-white/10 hover:border-primary/50 transition-all cursor-pointer">
                  <div className="flex flex-col items-center justify-center">
                    {phase === 'analyzing' ? (
                      <>
                        <RefreshCw className="w-10 h-10 text-primary animate-spin mb-4" />
                        <p className="font-bold">파일 분석 중...</p>
                        <p className="text-sm text-slate-500 mt-1">Claude AI가 회사 정보를 추출하고 있습니다</p>
                      </>
                    ) : (
                      <>
                        <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                          <Upload className="text-primary w-8 h-8" />
                        </div>
                        <p className="font-bold text-lg mb-1">회사 파일 업로드</p>
                        <p className="text-sm text-slate-500">PDF, HWP, DOCX 지원 · 회사소개서 또는 기존 사업계획서</p>
                      </>
                    )}
                  </div>
                  <input type="file" className="hidden" accept=".pdf,.hwp,.docx"
                    onChange={e => { if (e.target.files[0]) handleFileUpload(e.target.files[0]); }} />
                </label>
                <div className="mt-4 flex items-center justify-center gap-6 text-sm text-slate-500">
                  <div className="flex items-center gap-1.5"><Shield className="w-4 h-4" /> 보안 처리</div>
                  <div className="flex items-center gap-1.5"><Zap className="w-4 h-4" /> 즉시 분석</div>
                  <div className="flex items-center gap-1.5"><Bell className="w-4 h-4" /> 신규 공고 알림</div>
                </div>
              </motion.div>
            )}

            {/* Phase: Info Review */}
            {phase === 'info' && companyInfo && (
              <motion.div key="info" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="max-w-2xl mx-auto"
              >
                <div className="glass rounded-3xl p-6 mb-4">
                  <h2 className="font-bold text-lg mb-4">추출된 회사 정보</h2>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    {[
                      ['회사명', 'company_name'],
                      ['업종', 'industry'],
                      ['핵심 기술', 'core_tech'],
                      ['팀 규모', 'team_size'],
                      ['매출 현황', 'revenue'],
                    ].map(([label, key]) => (
                      <div key={key}>
                        <p className="text-slate-500 text-xs mb-1">{label}</p>
                        <input
                          className="w-full bg-white/5 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50"
                          value={companyInfo[key] || ''}
                          onChange={e => setCompanyInfo(p => ({ ...p, [key]: e.target.value }))}
                        />
                      </div>
                    ))}
                    <div className="col-span-2">
                      <p className="text-slate-500 text-xs mb-1">검색 키워드 (쉼표 구분)</p>
                      <input
                        className="w-full bg-white/5 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50"
                        value={(companyInfo.keywords || []).join(', ')}
                        onChange={e => setCompanyInfo(p => ({ ...p, keywords: e.target.value.split(',').map(k => k.trim()) }))}
                      />
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => handleMatchRequest(companyInfo)}
                  className="primary-btn w-full justify-center py-4"
                >
                  정부 공고 자동 매칭 시작 <ArrowRight className="w-5 h-5" />
                </button>
              </motion.div>
            )}

            {/* Phase: Matching */}
            {phase === 'matching' && (
              <motion.div key="matching" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="max-w-xl mx-auto text-center py-20"
              >
                <Search className="w-12 h-12 text-primary animate-pulse mx-auto mb-4" />
                <h2 className="font-bold text-xl mb-2">공고 매칭 중...</h2>
                <p className="text-slate-400">기업마당·K-Startup 공고와 Claude AI로 매칭하고 있습니다.</p>
              </motion.div>
            )}

            {/* Phase: Matches */}
            {phase === 'matches' && (
              <motion.div key="matches" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="font-bold text-xl">매칭된 공고 {matches.length}건</h2>
                    <p className="text-sm text-slate-400">신규 공고 발견 시 Discord/KakaoTalk으로 알림을 드립니다.</p>
                  </div>
                  <button
                    onClick={() => handleMatchRequest(companyInfo)}
                    className="flex items-center gap-2 px-4 py-2 glass rounded-xl text-sm hover:bg-white/10 transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" /> 재검색
                  </button>
                </div>

                {matches.length === 0 ? (
                  <div className="glass rounded-2xl p-10 text-center text-slate-400">
                    <Search className="w-8 h-8 mx-auto mb-3 opacity-40" />
                    <p>매칭된 공고가 없습니다. 키워드를 수정하거나 API Key를 확인하세요.</p>
                  </div>
                ) : (
                  <div className="grid md:grid-cols-2 gap-3">
                    {matches.map(m => (
                      <GrantCard key={m.id} match={m} onGenerate={handleGenerate} />
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* 계획서 생성 오버레이 */}
          <AnimatePresence>
            {generating && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-[#080810]/80 backdrop-blur-sm z-50 flex items-center justify-center"
              >
                <div className="glass rounded-3xl p-10 max-w-md w-full mx-4">
                  <div className="w-14 h-14 bg-primary/20 rounded-2xl flex items-center justify-center text-primary mb-6 mx-auto">
                    <BarChart2 className="w-7 h-7 animate-pulse" />
                  </div>
                  <h2 className="text-xl font-bold text-center mb-6">AI 계획서 생성 중</h2>
                  <div className="space-y-3">
                    {genSteps.map((step, i) => (
                      <div key={i} className={`flex items-center gap-3 transition-opacity ${i <= generationStep ? 'opacity-100' : 'opacity-20'}`}>
                        {i < generationStep ? (
                          <CheckCircle className="w-4 h-4 text-primary shrink-0" />
                        ) : i === generationStep ? (
                          <RefreshCw className="w-4 h-4 text-primary shrink-0 animate-spin" />
                        ) : (
                          <div className="w-4 h-4 rounded-full border border-slate-600 shrink-0" />
                        )}
                        <span className="text-sm">{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* 계획서 결과 사이드패널 */}
          <AnimatePresence>
            {proposalResult && (
              <ProposalResult result={proposalResult} onClose={() => setProposalResult(null)} />
            )}
          </AnimatePresence>

        </div>
      </main>

      {/* Trust Bar */}
      <section className="py-14 bg-white/[0.02] border-t border-white/5" id="how-it-works">
        <div className="container">
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { num: '01', color: 'blue', title: '공고 자동 탐지', desc: '기업마당·K-Startup 공고를 매일 스캔. 새 공고 발견 시 즉시 알림.' },
              { num: '02', color: 'purple', title: 'Deep Search 작성', desc: '공고 배점표를 분석해 배점 높은 항목에 집중. Claude Opus로 최고 품질 초안.' },
              { num: '03', color: 'cyan', title: 'Self-Refinement', desc: '심사관 AI가 약점을 지적하고 3라운드 보강. 합격 가능성 % 실시간 표시.' },
            ].map(({ num, color, title, desc }) => (
              <div key={num} className="p-7 glass rounded-3xl hover:bg-white/[0.05] transition-colors">
                <div className={`w-11 h-11 bg-${color}-500/10 rounded-xl flex items-center justify-center text-${color}-400 mb-5 font-bold text-xl`}>{num}</div>
                <h3 className="text-lg font-bold mb-3">{title}</h3>
                <p className="text-slate-400 text-sm">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-14 container" id="pricing">
        <h2 className="text-center text-3xl font-black mb-10">합리적인 가격</h2>
        <div className="grid md:grid-cols-3 gap-5 max-w-3xl mx-auto">
          {[
            { name: '프리', price: '무료', desc: '공고 매칭 3건/월, 계획서 초안 1건', highlight: false },
            { name: '스타터', price: '₩99,000', period: '/월', desc: '무제한 공고 알림 + 계획서 5건', highlight: true },
            { name: '프로', price: '₩299,000', period: '/월', desc: '무제한 + Self-Refinement + HWP 출력', highlight: false },
          ].map(({ name, price, period, desc, highlight }) => (
            <div key={name} className={`p-6 rounded-2xl ${highlight ? 'bg-primary/10 border border-primary/30' : 'glass'}`}>
              <div className="font-bold text-lg mb-1">{name}</div>
              <div className="text-3xl font-black mb-1">{price}<span className="text-sm font-normal text-slate-400">{period}</span></div>
              <p className="text-sm text-slate-400 mb-5">{desc}</p>
              <button className={`w-full py-2.5 rounded-xl text-sm font-semibold transition-colors ${highlight ? 'bg-primary text-white hover:bg-primary/80' : 'glass hover:bg-white/10'}`}>
                시작하기
              </button>
            </div>
          ))}
        </div>
      </section>

      <footer className="py-10 border-t border-white/5 text-center text-sm text-slate-500">
        <div className="container">
          <div className="flex justify-center gap-8 mb-4">
            <a href="#" className="hover:text-white">이용약관</a>
            <a href="#" className="hover:text-white">개인정보처리방침</a>
            <a href="#" className="hover:text-white">대표문의</a>
          </div>
          <p>© 2026 GrantAI. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default App;
