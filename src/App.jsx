import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, CheckCircle, Zap, Shield, Search, ArrowRight, X } from 'lucide-react';

const App = () => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [step, setStep] = useState(0);
  const [file, setFile] = useState(null);

  const steps = [
    { label: 'PDF 데이터 분석 중...', icon: <Search className="w-6 h-6" /> },
    { label: '실시간 정부지원금 매칭 중...', icon: <Zap className="w-6 h-6" /> },
    { label: '공무원 뇌구조 기반 초안 작성 중...', icon: <FileText className="w-6 h-6" /> },
    { label: 'HWP 네이티브 파일 생성 완료!', icon: <CheckCircle className="w-6 h-6" /> },
  ];

  const startProcessing = (e) => {
    e.preventDefault();
    if (!file) return;
    setIsProcessing(true);
    setStep(0);
  };

  useEffect(() => {
    if (isProcessing && step < steps.length - 1) {
      const timer = setTimeout(() => {
        setStep(s => s + 1);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [isProcessing, step]);

  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 glass">
        <div className="container h-20 flex items-center justify-between">
          <div className="text-2xl font-black gradient-text tracking-tighter">GrantAI.</div>
          <div className="hidden md:flex gap-8 text-sm font-medium text-slate-400">
            <a href="#how-it-works" className="hover:text-white transition-colors">이용 방법</a>
            <a href="#benefits" className="hover:text-white transition-colors">특징</a>
            <a href="#faq" className="hover:text-white transition-colors">FAQ</a>
          </div>
          <button className="px-5 py-2 glass rounded-full text-sm font-semibold hover:bg-white/10 transition-colors">
            문의하기
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="pt-40 pb-20 container relative">
        {/* Background Glow */}
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-primary/20 blur-[120px] -z-10 rounded-full" />
        
        <div className="max-w-4xl mx-auto text-center">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 glass rounded-full text-xs font-bold text-primary mb-8 tracking-widest uppercase"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            2026-04-09 실시간 업데이트 완료
          </motion.div>
          
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            회사소개서 PDF <span className="gradient-text">하나면 충분합니다.</span>
          </motion.h1>
          
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-xl md:text-2xl text-slate-400 mb-12 leading-relaxed"
          >
            이번 주 신청 가능한 모든 정부지원금을 매칭하고,<br className="hidden md:block" />
            <strong className="text-white">바로 제출 가능한 HWP 사업계획서 초안</strong>을 3분 안에 드립니다.
          </motion.p>

          {!isProcessing ? (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3 }}
              className="max-w-xl mx-auto"
            >
              <label 
                className="group relative flex flex-col items-center justify-center w-full h-64 glass rounded-3xl border-dashed border-2 border-white/10 hover:border-primary/50 transition-all cursor-pointer overflow-hidden"
              >
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    <Upload className="text-primary w-8 h-8" />
                  </div>
                  <p className="mb-2 text-lg font-bold">PDF 파일 업로드</p>
                  <p className="text-sm text-slate-500">회사소개서 또는 기존 사업계획서</p>
                </div>
                <input 
                  type="file" 
                  className="hidden" 
                  accept=".pdf"
                  onChange={(e) => {
                    setFile(e.target.files[0]);
                    startProcessing(e);
                  }}
                />
              </label>
              <div className="mt-6 flex items-center justify-center gap-6 text-sm text-slate-500">
                <div className="flex items-center gap-1.5"><Shield className="w-4 h-4" /> 보안 폐기 보장</div>
                <div className="flex items-center gap-1.5"><Zap className="w-4 h-4" /> 3분 이내 완료</div>
                <div className="flex items-center gap-1.5"><FileText className="w-4 h-4" /> HWP 네이티브 지원</div>
              </div>
            </motion.div>
          ) : (
            <div className="max-w-xl mx-auto glass rounded-3xl p-12 text-left relative overflow-hidden">
               {/* Progress Bar */}
               <div className="absolute top-0 left-0 h-1 bg-primary transition-all duration-500" style={{ width: `${(step + 1) / steps.length * 100}%` }} />
               
               <div className="flex items-center gap-4 mb-8">
                 <div className="w-12 h-12 bg-primary/20 rounded-xl flex items-center justify-center text-primary animate-pulse">
                   {steps[step].icon}
                 </div>
                 <div>
                   <h3 className="text-xl font-bold">{steps[step].label}</h3>
                   <p className="text-sm text-slate-400">AI가 데이터를 초고속으로 처리하고 있습니다.</p>
                 </div>
               </div>

               <div className="space-y-4">
                 {steps.map((s, i) => (
                   <div key={i} className={`flex items-center gap-3 transition-opacity duration-500 ${i <= step ? 'opacity-100' : 'opacity-20'}`}>
                     <CheckCircle className={`w-5 h-5 ${i < step ? 'text-primary' : 'text-slate-500'}`} />
                     <span className="text-sm font-medium">{s.label}</span>
                   </div>
                 ))}
               </div>

               {step === steps.length - 1 && (
                 <motion.div 
                   initial={{ opacity: 0, y: 10 }}
                   animate={{ opacity: 1, y: 0 }}
                   className="mt-8 pt-8 border-t border-white/10"
                 >
                   <button className="primary-btn w-full justify-center py-4">
                     HWP 결과물 다운로드 받기 (5만원) <ArrowRight className="w-5 h-5" />
                   </button>
                   <p className="text-center text-xs text-slate-500 mt-4">
                     결과물이 불만족스러우신가요? 100% 환불해 드립니다.
                   </p>
                 </motion.div>
               )}
            </div>
          )}
        </div>
      </header>

      {/* Trust Section */}
      <section className="py-20 bg-white/[0.02]" id="benefits">
        <div className="container">
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-8 glass rounded-3xl hover:bg-white/[0.05] transition-colors">
              <div className="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center text-blue-400 mb-6 font-bold text-2xl">01</div>
              <h3 className="text-xl font-bold mb-4">공무원 뇌구조 탑재</h3>
              <p className="text-slate-400">단순 작성이 아닙니다. 심사위원이 좋아하는 두괄식, 정량적 수치 기반의 '공공 언어'로 알아서 바꿔줍니다.</p>
            </div>
            <div className="p-8 glass rounded-3xl hover:bg-white/[0.05] transition-colors">
              <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center text-purple-400 mb-6 font-bold text-2xl">02</div>
              <h3 className="text-xl font-bold mb-4">HWP 원본 파일 제공</h3>
              <p className="text-slate-400">PDF나 Word는 다시 편집해야 합니다. GrantAI는 우리나라 표준인 HWP 포맷 그대로, 표와 서식까지 완벽하게 내보냅니다.</p>
            </div>
            <div className="p-8 glass rounded-3xl hover:bg-white/[0.05] transition-colors">
              <div className="w-12 h-12 bg-cyan-500/10 rounded-xl flex items-center justify-center text-cyan-400 mb-6 font-bold text-2xl">03</div>
              <h3 className="text-xl font-bold mb-4">실시간 공고 매칭</h3>
              <p className="text-slate-400">데이터를 올리는 순간, K-Startup과 Bizinfo의 최신 공고 5,000여 개를 전격 분석하여 매칭해 드립니다.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-white/5 text-center text-sm text-slate-500">
        <div className="container">
          <div className="flex justify-center gap-8 mb-6">
            <a href="#" className="hover:text-white">이용약관</a>
            <a href="#" className="hover:text-white">개인정보처리방침</a>
            <a href="#" className="hover:text-white">대표문의</a>
          </div>
          <p>© 2026 GrantAI. 본 서비스는 정식 런칭 전 선착순 테스트 버전입니다.</p>
        </div>
      </footer>
    </div>
  );
};

export default App;
